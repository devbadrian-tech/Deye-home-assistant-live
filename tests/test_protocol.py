"""Wire-format and safety tests; no LAN device is contacted."""

import struct
import unittest
from unittest.mock import patch

import importlib
from pathlib import Path
import sys
import types

package = types.ModuleType("test_wire_deye")
package.__path__ = [str(Path(__file__).resolve().parents[1] / "custom_components/deye_live")]
sys.modules["test_wire_deye"] = package
protocol = importlib.import_module("test_wire_deye.protocol")


class FakeSocket:
    def __init__(self, respond, fragment=1, tick=None):
        self.respond = respond
        self.fragment = fragment
        self.tick = tick
        self.buffer = b""
        self.requests = []
        self.timeouts = []
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def settimeout(self, timeout):
        self.timeouts.append(timeout)

    def sendall(self, data):
        self.requests.append(data)
        self.buffer = self.respond(data)

    def recv(self, size):
        if self.tick:
            self.tick()
        size = min(size, self.fragment)
        data, self.buffer = self.buffer[:size], self.buffer[size:]
        return data


def with_crc(data):
    return data + struct.pack("<H", protocol.crc16(data))


def tcp_reply(request, pdu=b"\x03\x04\x12\x34\xff\xff"):
    return request[:4] + struct.pack(">H", len(pdu) + 1) + request[6:7] + pdu


def v5_reply(request, rtu=None, control=0x1510, serial=None, sequence=None,
             payload=None):
    if payload is None:
        payload = b"\x02\x01" + bytes(12) + (
            rtu if rtu is not None else with_crc(b"\x01\x03\x04\x12\x34\xff\xff"))
    header = struct.pack("<BHHBBI", 0xa5, len(payload), control,
                         request[5] if sequence is None else sequence, 99,
                         struct.unpack("<I", request[7:11])[0] if serial is None else serial)
    frame = header + payload
    return frame + bytes((sum(frame[1:]) & 255, 0x15))


class ProtocolTests(unittest.TestCase):
    def read(self, fake, name="modbus-tcp", **kwargs):
        defaults = dict(host="192.0.2.1", port=502, protocol=name, unit=1,
                        start=0, count=2, timeout=3)
        if name == "solarman-v5":
            defaults["serial"] = 123456789
        defaults.update(kwargs)
        with patch.object(protocol.socket, "create_connection", return_value=fake):
            result = protocol.read_registers(**defaults)
        self.assertTrue(fake.closed)
        return result

    def test_known_modbus_crc_and_request(self):
        # Widely documented Modbus request: slave 1, read registers 0..9.
        self.assertEqual(protocol.crc16(bytes.fromhex("01030000000a")), 0xcdc5)
        fake = FakeSocket(lambda request: with_crc(b"\x01\x03\x04\x12\x34\xff\xff"))
        self.assertEqual(self.read(fake, "rtu-tcp"), [0x1234, 0xffff])
        self.assertEqual(fake.requests, [bytes.fromhex("010300000002c40b")])

    def test_all_non_read_function_codes_rejected_before_connect(self):
        with patch.object(protocol.socket, "create_connection") as connect:
            for function in range(256):
                if function in (3, 4):
                    continue
                with self.subTest(function=function), self.assertRaises(ValueError):
                    protocol.read_registers("192.0.2.1", 502, "modbus-tcp", 1,
                                            0, 1, function=function)
            connect.assert_not_called()

    def test_invalid_arguments_rejected_before_connect(self):
        invalid = [dict(unit=0), dict(unit=248), dict(unit=True), dict(start=-1),
                   dict(start=65536), dict(start=65535, count=2), dict(count=0),
                   dict(count=126), dict(count=1.5), dict(port=0), dict(port=65536),
                   dict(protocol="udp"), dict(function=True), dict(timeout=0),
                   dict(timeout=float("inf")), dict(timeout=float("nan")),
                   dict(timeout=True), dict(host=""), dict(host=" host"),
                   dict(protocol="solarman-v5"), dict(protocol="solarman-v5", serial=0),
                   dict(protocol="solarman-v5", serial=2**32)]
        with patch.object(protocol.socket, "create_connection") as connect:
            for changes in invalid:
                kwargs = dict(host="192.0.2.1", port=502, protocol="modbus-tcp",
                              unit=1, start=0, count=1)
                kwargs.update(changes)
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    protocol.read_registers(**kwargs)
            connect.assert_not_called()

    def test_modbus_tcp_one_byte_fragments_and_single_read_only_request(self):
        fake = FakeSocket(tcp_reply)
        self.assertEqual(self.read(fake), [0x1234, 0xffff])
        self.assertEqual(len(fake.requests), 1)
        request = fake.requests[0]
        self.assertEqual(request[2:], bytes.fromhex("00000006010300000002"))
        self.assertTrue(all(a >= b for a, b in zip(fake.timeouts, fake.timeouts[1:])))

    def test_function_four(self):
        fake = FakeSocket(lambda req: tcp_reply(req, b"\x04\x02\x00\x09"))
        self.assertEqual(self.read(fake, function=4, count=1), [9])
        self.assertEqual(fake.requests[0][7], 4)

    def test_exception_replies_across_transports(self):
        responses = {
            "modbus-tcp": lambda req: tcp_reply(req, b"\x83\x02"),
            "rtu-tcp": lambda req: with_crc(b"\x01\x83\x02"),
            "solarman-v5": lambda req: v5_reply(req, with_crc(b"\x01\x83\x02")),
        }
        for name, response in responses.items():
            with self.subTest(protocol=name), self.assertRaises(protocol.ModbusException) as error:
                self.read(FakeSocket(response), name)
            self.assertEqual(error.exception.code, 2)

    def test_tcp_rejects_wrong_ids_lengths_functions_counts(self):
        def mutate(index, value):
            def response(req):
                result = bytearray(tcp_reply(req))
                result[index] = value if value is not None else result[index] ^ 1
                return bytes(result)
            return response
        for index, value in [(0, None), (3, 1), (5, 0), (5, 254), (6, 2),
                             (7, 4), (8, 2)]:
            with self.subTest(index=index), self.assertRaises(protocol.ProtocolError):
                self.read(FakeSocket(mutate(index, value)))

    def test_truncated_response_is_not_a_successful_read(self):
        fake = FakeSocket(lambda req: tcp_reply(req)[:-1])
        with self.assertRaisesRegex(protocol.ProtocolError, "complete response"):
            self.read(fake)

    def test_rtu_rejects_bad_crc_and_wrong_unit(self):
        for frame in [bytes.fromhex("0103041234ffff0000"),
                      with_crc(b"\x02\x03\x04\x12\x34\xff\xff")]:
            with self.subTest(frame=frame.hex()), self.assertRaises(protocol.ProtocolError):
                self.read(FakeSocket(lambda req: frame), "rtu-tcp")

    def test_v5_one_byte_fragments_and_wire_layout(self):
        fake = FakeSocket(v5_reply)
        self.assertEqual(self.read(fake, "solarman-v5"), [0x1234, 0xffff])
        self.assertEqual(len(fake.requests), 1)
        frame = fake.requests[0]
        self.assertEqual(frame[:5], bytes.fromhex("a517001045"))
        self.assertEqual(frame[7:11], struct.pack("<I", 123456789))
        self.assertEqual(frame[11:26], b"\x02" + bytes(14))
        self.assertEqual(frame[26:-2], bytes.fromhex("010300000002c40b"))
        self.assertEqual(frame[-2:], bytes((sum(frame[1:-2]) & 255, 0x15)))

    def test_v5_known_double_crc_quirk(self):
        rtu = with_crc(b"\x01\x03\x04\x12\x34\xff\xff") + b"\x00\x00"
        fake = FakeSocket(lambda req: v5_reply(req, rtu))
        self.assertEqual(self.read(fake, "solarman-v5"), [0x1234, 0xffff])
        bad = rtu[:-4] + b"\xff\xff\x00\x00"
        with self.assertRaises(protocol.ProtocolError):
            self.read(FakeSocket(lambda req: v5_reply(req, bad)), "solarman-v5")

    def test_v5_skips_heartbeat_without_time_sync_reply(self):
        def reply(req):
            return v5_reply(req, control=0x4710, payload=b"\x00") + v5_reply(req)
        fake = FakeSocket(reply)
        self.assertEqual(self.read(fake, "solarman-v5"), [0x1234, 0xffff])
        self.assertEqual(len(fake.requests), 1)

    def test_v5_rejects_serial_sequence_checksum_or_non_inverter_reply(self):
        def bad_checksum(req):
            frame = bytearray(v5_reply(req))
            frame[-2] ^= 1
            return bytes(frame)
        responses = [lambda req: v5_reply(req, serial=98765),
                     lambda req: v5_reply(req, sequence=req[5] ^ 1),
                     bad_checksum,
                     lambda req: v5_reply(req, control=0x1110),
                     lambda req: v5_reply(req, payload=b"\x01" + bytes(20)),
                     lambda req: v5_reply(req, payload=b"\x02" + bytes(10))]
        for index, response in enumerate(responses):
            with self.subTest(index=index), self.assertRaises(protocol.ProtocolError):
                self.read(FakeSocket(response), "solarman-v5")

    def test_slow_stream_obeys_shared_deadline(self):
        clock = [100.0]
        def tick():
            clock[0] += 0.3
        fake = FakeSocket(tcp_reply, tick=tick)
        with patch.object(protocol.time, "monotonic", side_effect=lambda: clock[0]):
            with self.assertRaises(TimeoutError):
                self.read(fake, timeout=1)
        self.assertLess(len(fake.timeouts), 10)
        self.assertTrue(fake.closed)

    def test_maximum_read_count(self):
        pdu = b"\x03\xfa" + struct.pack(">125H", *range(125))
        fake = FakeSocket(lambda req: tcp_reply(req, pdu), fragment=31)
        self.assertEqual(self.read(fake, count=125), list(range(125)))


if __name__ == "__main__":
    unittest.main()
