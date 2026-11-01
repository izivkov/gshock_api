import unittest

from gshock_api.iolib.alarms_io import encode_secondary_alarms


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


if __name__ == "__main__":
    unittest.main()