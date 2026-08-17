from datetime import datetime
from typing import TYPE_CHECKING
import unittest

from gshock_api.iolib.alarms_io import AlarmsIOFunctional
from gshock_api.iolib.app_info_io import AppInfoIOFunctional
from gshock_api.iolib.button_pressed_io import ButtonPressedIOFunctional, WatchButton
from gshock_api.iolib.dst_for_world_cities_io import DstForWorldCitiesIOFunctional
from gshock_api.iolib.dst_watch_state_io import DstWatchStateIOFunctional

if TYPE_CHECKING:
    from gshock_api.iolib.settings_io import SettingsDict
from gshock_api.iolib.settings_io import SettingsIOFunctional
from gshock_api.iolib.time_adjustement_io import TimeAdjustmentIOFunctional
from gshock_api.iolib.time_io import TimeEncoder, TimeEncoderPure, TimeIOFunctional
from gshock_api.iolib.timer_io import TimerIOFunctional
from gshock_api.iolib.watch_condition_io import WatchConditionIOFunctional
from gshock_api.iolib.watch_name_io import WatchNameIOFunctional
from gshock_api.iolib.world_cities_io import WorldCitiesIOFunctional


class TestGShockFunctionalAPI(unittest.TestCase):
    # --- TimeIO Tests ---
    def test_deterministic_time_encoding(self):
        dt = datetime(2026, 5, 30, 8, 45, 30, 123456)
        encoded = TimeEncoderPure.encode_current_time(dt)
        self.assertEqual(len(encoded), 10)
        self.assertEqual(encoded[0], 0xEA)
        self.assertEqual(encoded[1], 0x07)
        self.assertEqual(encoded[2], 5)
        self.assertEqual(encoded[3], 30)
        self.assertEqual(encoded[4], 8)
        self.assertEqual(encoded[5], 45)
        self.assertEqual(encoded[6], 30)
        self.assertEqual(encoded[7], 5)
        expected_nano_byte = (123456000 * 256 // 1000000000) & 0xFF
        self.assertEqual(encoded[8], expected_nano_byte)
        self.assertEqual(encoded[9], 1)

    def test_legacy_time_compatibility(self):
        dt = datetime(2026, 5, 30, 8, 45, 30, 123456)
        legacy_arr = TimeEncoder.prepare_current_time(dt)
        pure_bytes = TimeEncoderPure.encode_current_time(dt)
        self.assertEqual(legacy_arr, bytearray(pure_bytes))

    def test_time_monoids(self):
        dt = datetime(2026, 5, 30, 8, 45, 30, 123456)
        encoded = TimeEncoderPure.encode_current_time(dt)
        
        # Monoid A: Identity
        self.assertEqual(encoded + b"", encoded)
        self.assertEqual(b"" + encoded, encoded)

        # Monoid B: Command lists
        commands = TimeIOFunctional.prepare_watch_commands('{"value": {}}', 1779979200.0)
        self.assertEqual(commands + [], commands)  # noqa: RUF005
        self.assertEqual([] + commands, commands)  # noqa: RUF005

    # --- AlarmsIO Tests ---
    def test_alarms_commands(self):
        commands = AlarmsIOFunctional.prepare_watch_commands()
        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[0].handle, 0x000C)
        self.assertEqual(commands[1].handle, 0x000C)

    # --- SettingsIO Tests ---
    def test_settings_encode_decode(self):
        from gshock_api.watch_info import watch_info
        watch_info.set_name_and_model("CASIO GW-B5600")
        settings_dict: SettingsDict = {
            "time_format": "24h",
            "button_tone": True,
            "auto_light": False,
            "power_saving_mode": True,
            "light_duration": "4s",
            "date_format": "DD:MM",
            "language": "French"
        }

        encoded = SettingsIOFunctional.encode(settings_dict)
        self.assertEqual(len(encoded), 12)
        self.assertEqual(encoded[0], 0x13)  # Protocol.SETTING_FOR_BASIC = 0x13
        
        decoded = SettingsIOFunctional.decode(encoded)
        self.assertEqual(decoded["time_format"], "24h")
        self.assertEqual(decoded["button_tone"], True)
        self.assertEqual(decoded["auto_light"], False)
        self.assertEqual(decoded["power_saving_mode"], True)
        self.assertEqual(decoded["light_duration"], "4s")
        self.assertEqual(decoded["date_format"], "DD:MM")
        self.assertEqual(decoded["language"], "French")
        watch_info.reset()

    def test_settings_commands(self):
        commands = SettingsIOFunctional.prepare_watch_commands()
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0].handle, 0x000C)
        self.assertEqual(commands[0].data, b"\x13")

    # --- TimerIO Tests ---
    def test_timer_encode_decode(self):
        seconds = 3665  # 1 hour, 1 minute, 5 seconds
        encoded = TimerIOFunctional.encode(seconds)
        self.assertEqual(encoded[0], 0x18)  # Protocol.TIMER = 0x18
        self.assertEqual(encoded[1], 1)     # Hours
        self.assertEqual(encoded[2], 1)     # Minutes
        self.assertEqual(encoded[3], 5)     # Seconds
        
        decoded = TimerIOFunctional.decode(encoded)
        self.assertEqual(decoded, seconds)

    def test_timer_commands(self):
        commands = TimerIOFunctional.prepare_watch_commands()
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0].handle, 0x000C)
        self.assertEqual(commands[0].data, b"\x18")

    # --- TimeAdjustmentIO Tests ---
    def test_time_adjustment_encode_decode(self):
        original_hex = "0x11 0F 0F 0F 06 00 50 00 04 00 01 00 80 10 D2"
        encoded = TimeAdjustmentIOFunctional.encode(original_hex, True, 25)
        
        decoded = TimeAdjustmentIOFunctional.decode(encoded)
        self.assertEqual(decoded["timeAdjusment"], "True")
        self.assertEqual(decoded["minutesAfterHour"], "25")

    # --- DstForWorldCitiesIO Tests ---
    def test_dst_for_world_cities_commands(self):
        commands = DstForWorldCitiesIOFunctional.prepare_watch_commands()
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0].handle, 0x000C)
        self.assertEqual(commands[0].data, b"\x1E")

    # --- DstWatchStateIO Tests ---
    def test_dst_watch_state_commands(self):
        commands = DstWatchStateIOFunctional.prepare_watch_commands()
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0].handle, 0x000C)
        self.assertEqual(commands[0].data, b"\x1D")

    # --- AppInfoIO Tests ---
    def test_app_info_commands(self):
        commands = AppInfoIOFunctional.prepare_watch_commands()
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0].handle, 0x000C)
        self.assertEqual(commands[0].data, b"\x22")

    def test_app_info_response(self):
        # Triggering packet
        trigger = bytes([0x22]) + bytes([0xFF] * 10) + bytes([0x00])
        response = AppInfoIOFunctional.prepare_watch_response(trigger)
        self.assertEqual(len(response), 1)
        self.assertEqual(response[0].handle, 0xE)
        self.assertEqual(response[0].data[0], 0x22)

    # --- WorldCitiesIO Tests ---
    def test_world_cities_commands(self):
        commands = WorldCitiesIOFunctional.prepare_watch_commands()
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0].handle, 0x000C)
        self.assertEqual(commands[0].data, b"\x1F")

    # --- ButtonPressedIO Tests ---
    def test_button_pressed_decode(self):
        # Left press payload example
        left_press = bytes([0x10, 0x17, 0x62, 0x07, 0x38, 0x85, 0xCD, 0x7F, 0x01] + [0] * 10)
        button = ButtonPressedIOFunctional.decode(left_press)
        self.assertEqual(button, WatchButton.LOWER_LEFT)

    # --- WatchConditionIO Tests ---
    def test_watch_condition_commands(self):
        commands = WatchConditionIOFunctional.prepare_watch_commands()
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0].handle, 0x000C)
        self.assertEqual(commands[0].data, b"\x28")

    # --- WatchNameIO Tests ---
    def test_watch_name_decode(self):
        payload = bytes([0x23]) + b"G-SHOCK" + b"\x00"
        name = WatchNameIOFunctional.decode(payload)
        self.assertEqual(name, "G-SHOCK")

    # --- MTG-B3000 Tests ---
    def test_mtg_b3000_alarms_commands(self):
        commands = AlarmsIOFunctional.prepare_watch_commands_mtg_b3000()
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0].handle, 0x000C)
        self.assertEqual(commands[0].data, b"\x15")

        alarm_msg = '{"value": [{"enabled": true, "hasHourlyChime": false, "hour": 7, "minute": 25}]}'
        set_commands = AlarmsIOFunctional.prepare_watch_commands_set_mtg_b3000(alarm_msg)
        self.assertEqual(len(set_commands), 1)
        self.assertEqual(set_commands[0].handle, 0x000E)
        self.assertEqual(set_commands[0].data, bytes([0x15, 0x40, 0x40, 7, 25]))

    def test_mtg_b3000_timer_encode(self):
        seconds = 600  # 10 minutes
        encoded = TimerIOFunctional.encode_mtg_b3000(seconds)
        self.assertEqual(len(encoded), 15)
        self.assertEqual(encoded[0], 0x18)  # Protocol.TIMER = 0x18
        self.assertEqual(encoded[1], 0)     # Hours
        self.assertEqual(encoded[2], 10)    # Minutes
        self.assertEqual(encoded[3], 0)     # Seconds
        self.assertEqual(encoded[4:], bytes([0]*11))  # Padding

        timer_msg = '{"value": 600}'
        set_commands = TimerIOFunctional.prepare_watch_commands_set_mtg_b3000(timer_msg)
        self.assertEqual(len(set_commands), 1)
        self.assertEqual(set_commands[0].handle, 0x000E)
        self.assertEqual(set_commands[0].data, encoded)

    def test_mtg_b3000_settings_encode_decode(self):
        from gshock_api.watch_info import watch_info, WatchModel
        watch_info.model = WatchModel.MTG_B3000

        settings_dict = {
            "time_format": "24h",
            "button_tone": True,
            "auto_light": False,
            "power_saving_mode": True,
            "light_duration": "3s",
            "date_format": "DD:MM",
            "language": "French"
        }
        encoded = SettingsIOFunctional.encode(settings_dict)
        self.assertEqual(encoded[2], 1)
        decoded = SettingsIOFunctional.decode(encoded)
        self.assertEqual(decoded["light_duration"], "3s")

        settings_dict["light_duration"] = "1.5s"
        encoded = SettingsIOFunctional.encode(settings_dict)
        self.assertEqual(encoded[2], 0)
        decoded = SettingsIOFunctional.decode(encoded)
        self.assertEqual(decoded["light_duration"], "1.5s")

        watch_info.reset()

    # --- WatchInfo & Protocol Tests ---
    def test_watch_info_exact_lookup_and_protocols(self):
        from gshock_api.watch_info import watch_info, WatchModel
        from gshock_api.protocols.mip_protocol import MipProtocol
        from gshock_api.protocols.analogue_protocol import AnalogueProtocol
        from gshock_api.protocols.standard_protocol import StandardProtocol

        watch_info.set_name_and_model("CASIO GW-BX5600")
        self.assertEqual(watch_info.model, WatchModel.GW_BX5600)
        self.assertTrue(watch_info.hasNewTimeFormat)
        self.assertIsInstance(watch_info.protocol, MipProtocol)

        watch_info.set_name_and_model("CASIO MTG-B1000")
        self.assertEqual(watch_info.model, WatchModel.MTG_B1000)
        self.assertTrue(watch_info.hasSecondDial)
        self.assertIsInstance(watch_info.protocol, AnalogueProtocol)

        watch_info.set_name_and_model("CASIO ABL-100WE")
        self.assertEqual(watch_info.model, WatchModel.ABL_100)
        self.assertTrue(watch_info.hasStepCounter)
        self.assertIsInstance(watch_info.protocol, StandardProtocol)

        watch_info.set_name_and_model("CASIO GW-B5600")
        self.assertEqual(watch_info.model, WatchModel.GW)
        self.assertEqual(watch_info.worldCitiesCount, 6)
        self.assertIsInstance(watch_info.protocol, StandardProtocol)
        watch_info.reset()

    # --- Step Counter Tests ---
    def test_step_counter_data_and_parse(self):
        from gshock_api.step_counter_data import StepCounterData
        from gshock_api.iolib.step_counter_io import StepCounterIOFunctional

        unavail = StepCounterData.unavailable()
        self.assertEqual(unavail.current_day_steps, None)
        self.assertEqual(unavail.hourly_steps, [])

        payload = bytearray(400)
        payload[0] = 0x26  # Header
        payload[1] = 1     # Mon
        payload[2] = 8     # Aug
        payload[3] = 17    # 17th

        for i in range(144):
            struct_offset = 6 + i * 2
            payload[struct_offset:struct_offset + 2] = (10 + i).to_bytes(2, "little")

        for i in range(14):
            struct_offset = 318 + i * 4
            payload[struct_offset:struct_offset + 4] = (5000 + i).to_bytes(4, "little")

        payload[374:378] = (12345).to_bytes(4, "little")

        parsed = StepCounterIOFunctional.parse(bytes(payload))
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.day_of_week, 1)
        self.assertEqual(parsed.month, 8)
        self.assertEqual(parsed.day_of_month, 17)
        self.assertEqual(parsed.current_day_steps, 12345)
        self.assertEqual(len(parsed.hourly_steps), 144)
        self.assertEqual(parsed.hourly_steps[0], 10)
        self.assertEqual(len(parsed.daily_history), 14)
        self.assertEqual(parsed.daily_history[0], 5000)

    # --- CasioTimeZoneHelper Tests ---
    def test_casio_time_zone_helper(self):
        from gshock_api.casio_time_zone_helper import CasioTimeZoneHelper

        lat, lon, exact = CasioTimeZoneHelper.get_world_city_coordinates("Europe/Madrid")
        self.assertTrue(exact)
        self.assertAlmostEqual(lat, 41.4548, places=4)
        self.assertAlmostEqual(lon, 2.2502, places=4)

        tz = CasioTimeZoneHelper.find_time_zone("Europe/London")
        self.assertEqual(tz.name, "LONDON")
        self.assertEqual(tz.zone_name, "Europe/London")

    # --- GwBx5600 Time IO City Records Test ---
    def test_gw_bx5600_city_records(self):
        from gshock_api.iolib.gw_bx5600_time_io import GwBx5600TimeIO

        city_records = GwBx5600TimeIO._build_world_city_records()
        self.assertEqual(len(city_records), 66)  # 3 x 22 bytes
        self.assertEqual(city_records[0], 0x14)
        self.assertEqual(city_records[1], 0x00)
        self.assertEqual(city_records[2], 0x24)
        self.assertEqual(city_records[3], 0x00)  # Slot 0
        self.assertEqual(city_records[4], 0x01)  # Flag


if __name__ == "__main__":
    unittest.main()