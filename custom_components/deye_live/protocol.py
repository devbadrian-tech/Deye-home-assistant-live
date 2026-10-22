"""Small, read-only Modbus clients using Python's standard library.

Only function 03 (holding registers) and 04 (input registers) can be sent.
Each call opens one TCP connection, sends one register read, then closes it.
Socket send/receive operations share a deadline; no retry or write occurs.

Solarman V5 layout reference (reverse engineered, not a vendor guarantee):
https://github.com/jmccrohan/pysolarmanv5/blob/main/docs/solarmanv5_protocol.rst
V5 heartbeat/info messages are ignored, never acknowledged with time updates.
Loggers requiring that handshake, encrypted V5, or disabled local access are
unsupported. A successful read does not establish the inverter's register map
or the age of measurements cached by the logger.
"""

import math
import secrets
import socket
import struct
import time
from typing import List, Optional


PROTOCOLS = ("modbus-tcp", "rtu-tcp", "solarman-v5")


class ProtocolError(Exception):
    """The peer's reply did not match the requested read or failed validation."""


class ModbusException(ProtocolError):
    """The inverter returned a valid Modbus exception instead of registers."""

    def __init__(self, code: int):
        self.code = code
        meanings = {
            1: "illegal function", 2: "illegal register address",
            3: "illegal data value", 4: "device failure", 5: "acknowledge",
            6: "device busy", 8: "memory parity error",
            10: "gateway path unavailable", 11: "gateway target did not respond",
        }
        super().__init__("Modbus exception 0x%02x: %s" % (
            code, meanings.get(code, "unknown exception")))


def _integer(value: int, low: int, high: int, name: str) -> None:
    if type(value) is not int or not low <= value <= high:
        raise ValueError("%s must be an integer from %d to %d" % (name, low, high))


def _validate(host, port, protocol, unit, start, count, function, timeout, serial):
    if not isinstance(host, str) or not host.strip() or host != host.strip():
        raise ValueError("host must be a nonempty hostname or IP address")
    _integer(port, 1, 65535, "port")
    if protocol not in PROTOCOLS:
        raise ValueError("protocol must be one of: " + ", ".join(PROTOCOLS))
    _integer(unit, 1, 247, "unit")  # Never send broadcast reads.
    _integer(start, 0, 65535, "start")
    _integer(count, 1, 125, "count")
    if start + count > 65536:
        raise ValueError("register range extends beyond address 65535")
    if type(function) is not int or function not in (3, 4):
        raise ValueError("READ ONLY: only Modbus function 3 or 4 is allowed")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise ValueError("timeout must be a positive finite number")
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be a positive finite number")
    if protocol == "solarman-v5":
        _integer(serial, 1, 0xffffffff, "logger serial")
    elif serial is not None:
        _integer(serial, 1, 0xffffffff, "logger serial")


def crc16(data: bytes) -> int:
    """Return the Modbus RTU CRC; transmit its low byte first."""
    crc = 0xffff
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0xa001 if crc & 1 else 0)
    return crc


def _with_crc(data: bytes) -> bytes:
    return data + struct.pack("<H", crc16(data))


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("response deadline exceeded")
    return remaining


def _receive(sock: socket.socket, size: int, deadline: float) -> bytes:
    result = bytearray()
    while len(result) < size:
        sock.settimeout(_remaining(deadline))
        chunk = sock.recv(size - len(result))
        if not chunk:
            raise ProtocolError("connection closed before the complete response arrived")
        result.extend(chunk)
    return bytes(result)


def _decode_pdu(pdu: bytes, function: int, count: int) -> List[int]:
    if not pdu:
        raise ProtocolError("empty Modbus response")
    if pdu[0] == (function | 0x80):
        if len(pdu) != 2:
            raise ProtocolError("invalid Modbus exception length")
        raise ModbusException(pdu[1])
    if pdu[0] != function:
        raise ProtocolError("response function does not match the read request")
    if len(pdu) < 2 or pdu[1] != count * 2 or len(pdu) != 2 + count * 2:
        raise ProtocolError("response register count or length does not match the request")
    return list(struct.unpack(">%dH" % count, pdu[2:]))


def _decode_rtu(frame: bytes, unit: int, function: int, count: int) -> List[int]:
    if len(frame) < 5 or len(frame) > 255:
        raise ProtocolError("invalid Modbus RTU response length")
    if frame[0] != unit:
        raise ProtocolError("response unit does not match the read request")
    if crc16(frame[:-2]) != struct.unpack("<H", frame[-2:])[0]:
        raise ProtocolError("invalid Modbus RTU CRC")
    return _decode_pdu(frame[1:-2], function, count)


def _read_tcp(sock, transaction, unit, function, count, deadline):
    header = _receive(sock, 7, deadline)
    received_transaction, protocol, length, received_unit = struct.unpack(">HHHB", header)
    if received_transaction != transaction:
        raise ProtocolError("Modbus transaction ID does not match the read request")
    if protocol != 0:
        raise ProtocolError("invalid Modbus TCP protocol identifier")
    if received_unit != unit:
        raise ProtocolError("response unit does not match the read request")
    if not 3 <= length <= 253:
        raise ProtocolError("invalid Modbus TCP response length")
    return _decode_pdu(_receive(sock, length - 1, deadline), function, count)


def _read_rtu(sock, unit, function, count, deadline):
    header = _receive(sock, 3, deadline)
    if header[0] != unit:
        raise ProtocolError("response unit does not match the read request")
    if header[1] == (function | 0x80):
        size = 2  # CRC, following the exception code already in the header.
    elif header[1] == function:
        if header[2] != count * 2:
            raise ProtocolError("response register count does not match the request")
        size = header[2] + 2
    else:
        raise ProtocolError("response function does not match the read request")
    return _decode_rtu(header + _receive(sock, size, deadline), unit, function, count)


def _v5_request(rtu: bytes, sequence: int, serial: int) -> bytes:
    payload = b"\x02" + b"\x00" * 14 + rtu
    header = struct.pack("<BHHBBI", 0xa5, len(payload), 0x4510, sequence, 0, serial)
    frame = header + payload
    return frame + bytes((sum(frame[1:]) & 0xff, 0x15))


def _read_v5(sock, sequence, serial, unit, function, count, deadline):
    while True:
        header = _receive(sock, 11, deadline)
        start, length, control, echoed_sequence, _, received_serial = struct.unpack(
            "<BHHBBI", header)
        if start != 0xa5:
            raise ProtocolError("invalid Solarman V5 start byte")
        if length > 1024:
            raise ProtocolError("Solarman V5 payload exceeds the supported length")
        body = _receive(sock, length + 2, deadline)
        if body[-1] != 0x15 or body[-2] != (sum(header[1:] + body[:-2]) & 0xff):
            raise ProtocolError("invalid Solarman V5 checksum or end byte")
        if received_serial != serial:
            raise ProtocolError("Solarman V5 logger serial does not match the request")
        if control in (0x4110, 0x4210, 0x4310, 0x4710, 0x4810):
            # No time synchronization or handshake replies: this client only reads.
            continue
        if control != 0x1510:
            raise ProtocolError("unsupported Solarman V5 response control code")
        if echoed_sequence != sequence:
            raise ProtocolError("Solarman V5 sequence does not match the request")
        payload = body[:-2]
        if len(payload) < 19 or payload[0] != 2:
            raise ProtocolError("Solarman V5 reply does not contain an inverter RTU frame")
        rtu = payload[14:]
        # Some Deye loggers append a second CRC (0000) to an already valid RTU
        # frame. Accept ONLY the exact expected length + 2 and a valid inner CRC.
        expected = 5 if rtu[1] == (function | 0x80) else 5 + 2 * count
        if len(rtu) == expected + 2 and rtu[-2:] == b"\x00\x00":
            candidate = rtu[:-2]
            if crc16(candidate[:-2]) == struct.unpack("<H", candidate[-2:])[0]:
                rtu = candidate
        return _decode_rtu(rtu, unit, function, count)


def read_registers(host: str, port: int, protocol: str, unit: int, start: int,
                   count: int, function: int = 3, timeout: float = 3.0,
                   serial: Optional[int] = None) -> List[int]:
    """Read zero-based register addresses; never write or change device settings.

    ``protocol`` is modbus-tcp, rtu-tcp, or solarman-v5. V5 requires the logger's
    numeric serial number (not the inverter serial). Values remain unsigned raw
    16-bit registers because the map/scaling depends on the exact inverter.
    ``timeout`` bounds connect and the shared socket I/O deadline; OS hostname
    resolution, if a hostname is used, is outside socket timeout control.
    """
    _validate(host, port, protocol, unit, start, count, function, timeout, serial)
    pdu = struct.pack(">BHH", function, start, count)
    transaction = secrets.randbelow(65536)
    sequence = secrets.randbelow(255) + 1
    if protocol == "modbus-tcp":
        request = struct.pack(">HHHB", transaction, 0, len(pdu) + 1, unit) + pdu
    else:
        request = _with_crc(bytes((unit,)) + pdu)
        if protocol == "solarman-v5":
            request = _v5_request(request, sequence, serial)
    deadline = time.monotonic() + timeout
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.settimeout(_remaining(deadline))
        sock.sendall(request)
        if protocol == "modbus-tcp":
            return _read_tcp(sock, transaction, unit, function, count, deadline)
        if protocol == "rtu-tcp":
            return _read_rtu(sock, unit, function, count, deadline)
        return _read_v5(sock, sequence, serial, unit, function, count, deadline)
