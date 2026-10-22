import importlib
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

package = types.ModuleType("isolated_deye")
package.__path__ = [str(Path(__file__).resolve().parents[1] / "custom_components/deye_live")]
sys.modules["isolated_deye"] = package
client = importlib.import_module("isolated_deye.client")

# Synthetic fixtures, not measurements from a real installation.
IDENTITY = [3, 1, 513] + [int.from_bytes(b'1234567890'[i:i+2], 'big') for i in range(0,10,2)]
POWER = [0] * 23
for register, value in {169:65500, 175:960, 178:960, 183:5120, 184:62, 190:1000, 191:1953}.items():
    POWER[register-169] = value
LIMITS = [50, 60, 0, 1, 1, 8, 990, 10, 30, 20]
SCHEDULE = [1,0,0,400,1100,1500,1700,2100] + [5000]*6 + [4900]*6 + [20,20,80,20,20,20] + [4,4,5,4,4,4]


class ClientTests(unittest.TestCase):
    def response(self, host, port, protocol, unit, start, count, **kw):
        self.assertEqual(kw['function'],3)
        return {(0,8):IDENTITY, (169,23):POWER, (79,1):[5001], (210,10):LIMITS, (248,32):SCHEDULE}[start,count]

    def test_live_and_limit_decoding(self):
        with patch.object(client, 'read_registers', side_effect=self.response):
            c = client.DeyeClient('logger', expected_serial='1234567890')
            data = c.poll()
            self.assertEqual(data['readings']['grid_power'],-36)
            self.assertEqual(data['readings']['battery_current'],19.53)
            self.assertEqual(data['limits']['shutdown_soc'],10)
            self.assertEqual(data['limits']['low_soc'],20)
            self.assertEqual(data['limits']['schedule_target_max'],80)
            self.assertEqual(data['limits']['schedule'][2]['start'],'11:00')

    def test_identity_change_rejected_before_power_read(self):
        with patch.object(client,'read_registers',return_value=IDENTITY) as read:
            with self.assertRaises(client.ProtocolError): client.DeyeClient('logger',expected_serial='wrong').poll()
            self.assertEqual(read.call_count,1)

    def test_unsupported_family_rejected(self):
        with self.assertRaises(client.ProtocolError): client.decode_identity([5]+IDENTITY[1:])

    def test_failure_does_not_reuse_telemetry(self):
        c = client.DeyeClient('logger')
        with patch.object(client,'read_registers',side_effect=self.response): c.poll()
        with patch.object(client,'read_registers',side_effect=TimeoutError):
            with self.assertRaises(TimeoutError): c.poll()

    def test_optional_limits_do_not_break_power_and_old_limits_are_discarded(self):
        c = client.DeyeClient('logger')
        with patch.object(client,'read_registers',side_effect=self.response): c.poll()
        c._next_limits = 0
        def read(*args,**kw):
            if args[4] in (210,248): raise client.ProtocolError('unsupported')
            return self.response(*args,**kw)
        with patch.object(client,'read_registers',side_effect=read): data=c.poll()
        self.assertEqual(data['limits'],{})
        self.assertEqual(data['readings']['load_power'],960)

    def test_signed_inversion_and_invalid_soc(self):
        data=client.decode_power(POWER, True, True)
        self.assertEqual(data['grid_power'],36)
        self.assertEqual(data['battery_power'],-1000)
        p=list(POWER);p[184-169]=65535
        with self.assertRaises(client.ProtocolError):client.decode_power(p)

    def test_invalid_settings_not_reported_as_zero(self):
        self.assertNotIn('shutdown_soc',client.decode_limits(LIMITS[:7]+[65535,30,20]))
        bad=list(SCHEDULE);bad[2]=2460
        with self.assertRaises(client.ProtocolError): client.decode_schedule(bad)

    def test_settings_poll_throttled(self):
        c=client.DeyeClient('logger')
        with patch.object(client,'read_registers',side_effect=self.response) as read:
            c.poll(); c.poll()
            self.assertEqual(sum(x.args[4]==210 for x in read.call_args_list),1)

if __name__=='__main__': unittest.main()
