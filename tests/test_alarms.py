import json
import unittest

from gshock_api.iolib.alarms_io import encode_secondary_alarms
from gshock_api.protocols.standard_protocol import StandardProtocol
from gshock_api.watch_info import watch_info


def alarm(hour: int, minute: int, enabled: bool = True) -> dict:
    return {"enabled": enabled, "hasHourlyChime": False, "hour": hour, "minute": minute}


class TestSecondaryAlarms(unittest.TestCase):
    def test_secondary_frame_encodes_the_alarms_passed_in(self):
        requested = [alarm(7, 25), alarm(8, 0), alarm(18, 34), alarm(19, 53), alarm(6, 14)]
        frame = bytes(encode_secondary_alarms(requested))

        # Entries are 4 bytes each: flag, constant, hour, minute. Skip the 1-byte header.
        entries = [(frame[i + 2], frame[i + 3]) for i in range(1, len(frame), 4)]
        self.assertEqual(entries, [(8, 0), (18, 34), (19, 53), (6, 14)])

    def test_fewer_than_two_alarms_writes_nothing(self):
        self.assertEqual(bytes(encode_secondary_alarms([alarm(7, 25)])), b"")

    def test_set_alarms_uses_last_alarm_slot_for_watch_alarm_count(self):
        class DummyConnection:
            def __init__(self):
                self.messages = []

            async def send_message(self, message):
                self.messages.append(message)

        original_model = watch_info.model
        original_info = watch_info.info
        try:
            watch_info.set_name_and_model("CASIO MTG-B3000")
            connection = DummyConnection()
            alarms = [
                {"enabled": True, "hasHourlyChime": False, "hour": 7, "minute": 25},
            ]
            import asyncio
            asyncio.run(StandardProtocol().set_alarms(connection, alarms, snooze_alarm5=True))
            payload = json.loads(connection.messages[0])
            self.assertTrue(payload["value"][0]["snooze"])
            self.assertFalse(payload["value"][0].get("oneTime", False))
        finally:
            watch_info.model = original_model
            watch_info.info = original_info


if __name__ == "__main__":
    unittest.main()