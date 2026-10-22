"""Read-only SG04LP1 client. No Home Assistant or external dependencies."""
from datetime import datetime, timezone
import time

from .protocol import ProtocolError, read_registers


def signed(value):
    return value - 65536 if value & 0x8000 else value


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def decode_identity(words):
    if words[0] not in (3, 0x0300):
        raise ProtocolError("Unsupported inverter family; this profile is for SG0xLP1")
    serial = b"".join(w.to_bytes(2, "big") for w in words[3:8]).decode("ascii", "strict").strip("\x00 ")
    if not serial or not serial.isalnum():
        raise ProtocolError("Invalid inverter serial")
    return serial


def decode_power(words, invert_grid=False, invert_battery=False):
    """Decode the single contiguous read 169..191. Positive = import/discharge."""
    r = dict(enumerate(words, 169))
    if len(words) != 23 or not 0 <= r[184] <= 100 or r[183] > 10000:
        raise ProtocolError("Invalid SG04LP1 telemetry values")
    battery_sign = -1 if invert_battery else 1
    return {
        "grid_power": signed(r[169]) * (-1 if invert_grid else 1),
        "inverter_power": signed(r[175]),
        "load_power": r[178],
        "battery_voltage": round(r[183] * 0.01, 2),
        "battery_soc": r[184],
        "pv1_power": r[186], "pv2_power": r[187],
        "solar_power": r[186] + r[187],
        "battery_power": signed(r[190]) * battery_sign,
        "battery_current": round(signed(r[191]) * 0.01 * battery_sign, 2),
    }


def decode_limits(words):
    """210..219. Invalid optional fields are absent, never made into zero."""
    r = dict(enumerate(words, 210))
    fields = {"max_charge_current": (210, 240), "max_discharge_current": (211, 240),
              "shutdown_soc": (217, 100), "restart_soc": (218, 100), "low_soc": (219, 100)}
    return {key: r[address] for key, (address, maximum) in fields.items()
            if address in r and 0 <= r[address] <= maximum}


def decode_schedule(words):
    """248..279. Targets are scheduled SOC values, not a battery charge ceiling."""
    if len(words) != 32:
        raise ProtocolError("Incomplete schedule")
    slots = []
    for i in range(6):
        hhmm, target = words[2 + i], words[20 + i]
        hours, minutes = divmod(hhmm, 100)
        if hours > 23 or minutes > 59 or target > 100:
            raise ProtocolError("Invalid schedule values")
        slots.append({"start": f"{hours:02}:{minutes:02}", "target_soc": target,
                      "grid_charge": bool(words[26 + i] & 1)})
    return {"schedule_enabled": bool(words[0] & 1), "schedule_mask": words[0],
            "schedule": slots,
            "schedule_target_min": min(s["target_soc"] for s in slots),
            "schedule_target_max": max(s["target_soc"] for s in slots)}


class DeyeClient:
    """Serial calls only. All transmitted requests are hard-coded FC03 reads."""

    def __init__(self, host, port=502, unit=1, expected_serial=None,
                 invert_grid=False, invert_battery=False, timeout=2.0):
        self.host, self.port, self.unit = host, port, unit
        self.expected_serial = expected_serial
        self.invert_grid, self.invert_battery = invert_grid, invert_battery
        self.timeout = timeout
        self._next_limits = 0.0
        self._limits = {}
        self._limits_at = None

    def _read(self, start, count):
        return read_registers(self.host, self.port, "modbus-tcp", self.unit,
                              start, count, function=3, timeout=self.timeout)

    def identify(self):
        try:
            serial = decode_identity(self._read(0, 8))
        except (UnicodeError, ValueError) as err:
            raise ProtocolError("Invalid inverter identity") from err
        if self.expected_serial and serial != self.expected_serial:
            raise ProtocolError("Inverter serial changed; refusing to read another device")
        return serial

    def poll(self):
        started = timestamp()
        serial = self.identify()
        readings = decode_power(self._read(169, 23), self.invert_grid, self.invert_battery)
        # Frequency is optional: its absence must not hide valid power readings.
        try:
            readings["grid_frequency"] = round(self._read(79, 1)[0] * 0.01, 2)
        except (OSError, ProtocolError):
            readings["grid_frequency"] = None
        received = timestamp()
        if time.monotonic() >= self._next_limits:
            self._next_limits = time.monotonic() + 60
            self._limits, self._limits_at = {}, None
            try:
                self._limits = decode_limits(self._read(210, 10))
                self._limits_at = timestamp()
            except (OSError, ProtocolError):
                pass
            try:
                self._limits.update(decode_schedule(self._read(248, 32)))
                self._limits["schedule_read_at"] = timestamp()
            except (OSError, ProtocolError):
                pass
        return {"serial": serial, "request_started_at": started, "sampled_at": received,
                "readings": readings, "limits": dict(self._limits),
                "limits_read_at": self._limits_at}
