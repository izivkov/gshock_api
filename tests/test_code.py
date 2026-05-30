from datetime import datetime
import json
import unittest

from gshock_api.iolib.actions import Write
from gshock_api.iolib.time_io import TimeEncoder, TimeEncoderPure, TimeIOFunctional


class TestTimeIOFunctional(unittest.TestCase):
    def test_deterministic_encoding(self):
        # A known static datetime: 2026-05-30 08:45:30.123456 (Saturday, so weekday index = 5)
        dt = datetime(2026, 5, 30, 8, 45, 30, 123456)
        
        encoded = TimeEncoderPure.encode_current_time(dt)
        self.assertEqual(len(encoded), 10)
        
        # Verify year (2026 = 0x07EA, little endian: EA 07)
        self.assertEqual(encoded[0], 0xEA)
        self.assertEqual(encoded[1], 0x07)
        
        # Verify month, day, hour, minute, second, weekday
        self.assertEqual(encoded[2], 5)    # May
        self.assertEqual(encoded[3], 30)   # 30th
        self.assertEqual(encoded[4], 8)    # Hour 8
        self.assertEqual(encoded[5], 45)   # Minute 45
        self.assertEqual(encoded[6], 30)   # Second 30
        self.assertEqual(encoded[7], 5)    # Saturday = index 5 (Monday = 0)
        
        # Verify nanos byte (123456 * 1000 = 123456000 nanos)
        # The calculation is (nanos * 256 // 1000000000) anded with 255.
        expected_nano_byte = (123456000 * 256 // 1000000000) & 0xFF
        self.assertEqual(encoded[8], expected_nano_byte)
        
        # Verify constant flag byte
        self.assertEqual(encoded[9], 1)

    def test_legacy_compatibility(self):
        dt = datetime(2026, 5, 30, 8, 45, 30, 123456)
        legacy_arr = TimeEncoder.prepare_current_time(dt)
        pure_bytes = TimeEncoderPure.encode_current_time(dt)
        
        self.assertEqual(legacy_arr, bytearray(pure_bytes))

    def test_monoid_a_binary_properties(self):
        dt = datetime(2026, 5, 30, 8, 45, 30, 123456)
        encoded = TimeEncoderPure.encode_current_time(dt)
        
        # Monoid A: Identity Element (b"")
        identity = b""
        self.assertEqual(encoded + identity, encoded)
        self.assertEqual(identity + encoded, encoded)
        
        # Monoid A: Associativity
        piece1 = encoded[:3]
        piece2 = encoded[3:7]
        piece3 = encoded[7:]
        self.assertEqual((piece1 + piece2) + piece3, piece1 + (piece2 + piece3))

    def test_monoid_b_command_stream_properties(self):
        system_time = 1779979200.0  # static unix timestamp
        msg_json = TimeIOFunctional.generate_request_message(system_time, 0)
        
        commands = TimeIOFunctional.prepare_watch_commands(msg_json, system_time)
        self.assertEqual(len(commands), 1)
        self.assertIsInstance(commands[0], Write)
        self.assertEqual(commands[0].handle, 0x000E)
        
        # Monoid B: Identity Element ([])
        identity = []
        self.assertEqual(commands + identity, commands)
        self.assertEqual(identity + commands, commands)
        
        # Monoid B: Associativity
        c1 = [commands[0]]
        c2 = [Write(handle=0x000C, data=b"\x01")]
        c3 = [Write(handle=0x000D, data=b"\x02")]
        self.assertEqual((c1 + c2) + c3, c1 + (c2 + c3))

    def test_generate_request_message(self):
        current_time = 1779979200.0
        offset = -18000
        msg_json = TimeIOFunctional.generate_request_message(current_time, offset)
        
        data = json.loads(msg_json)
        self.assertEqual(data["action"], "SET_TIME")
        self.assertEqual(data["value"]["time"], round(current_time))
        self.assertEqual(data["value"]["offset"], offset)


if __name__ == "__main__":
    unittest.main()