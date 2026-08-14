import json
from typing import Literal, TypedDict

from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.iolib.actions import BLEAction, Write
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.iolib.packet import Protocol
from gshock_api.logger import logger
from gshock_api.settings import settings
from gshock_api.utils import to_compact_string, to_hex_string, to_int_array
from gshock_api.watch_info import watch_info, WatchModel

CHARACTERISTICS: dict[str, int] = CasioConstants.CHARACTERISTICS


class SettingsDict(TypedDict):
    time_format: Literal["24h", "12h"]
    button_tone: bool
    auto_light: bool
    power_saving_mode: bool
    light_duration: Literal["4s", "2s", "3s", "1.5s"]
    date_format: Literal["DD:MM", "MM:DD"]
    language: Literal["English", "Spanish", "French", "German", "Italian", "Russian"]


class MtgB3000SettingsDict(TypedDict):
    """
    Only the fields confirmed to have real effect on the MTG-B3000.
    time_format, auto_light, date_format, and language are omitted —
    they don't apply to this model (auto_light: no ambient light sensor;
    date_format/language: no alphanumeric display to render them on).
    """
    button_tone: bool
    power_saving_mode: bool
    light_duration: Literal["4s", "2s", "3s", "1.5s"]


class SettingsIOFunctional:
    """
    Pure functional settings modules implementing Monoids.
    """

    @staticmethod
    def encode(settings_dict: SettingsDict) -> bytes:
        mask_24_hours = 0b00000001
        mask_button_tone_off = 0b00000010
        mask_light_off = 0b00000100
        power_saving_mode = 0b00010000

        arr = bytearray(12)
        arr[0] = Protocol.SETTING_FOR_BASIC.value
        if settings_dict["time_format"] == "24h":
            arr[1] |= mask_24_hours
        if not settings_dict["button_tone"]:
            arr[1] |= mask_button_tone_off
        if not settings_dict["auto_light"]:
            arr[1] |= mask_light_off
        if not settings_dict["power_saving_mode"]:
            arr[1] |= power_saving_mode

        long_duration = watch_info.longLightDuration if watch_info.longLightDuration else "4s"
        if settings_dict["light_duration"] == long_duration:
            arr[2] = 1
        if settings_dict["date_format"] == "DD:MM":
            arr[4] = 1

        language_index = {
            "English": 0,
            "Spanish": 1,
            "French": 2,
            "German": 3,
            "Italian": 4,
            "Russian": 5,
        }
        arr[5] = language_index.get(settings_dict["language"], 0)

        return bytes(arr)

    @staticmethod
    def encode_mtg_b3000(settings_dict: MtgB3000SettingsDict) -> bytes:
        """
        Same 12-byte wire format as encode(), but only sets the bits/bytes
        that actually matter for this model. time_format, auto_light,
        date_format, and language bytes are left at their existing observed
        defaults (24h format on, auto_light bit left "on"/0, date_format and
        language left at index 0) since this model doesn't expose them.
        """
        mask_24_hours = 0b00000001
        mask_button_tone_off = 0b00000010
        power_saving_mode_off = 0b00010000

        arr = bytearray(12)
        arr[0] = Protocol.SETTING_FOR_BASIC.value
        arr[1] |= mask_24_hours  # keep 24h format, matches observed watch state
        if not settings_dict["button_tone"]:
            arr[1] |= mask_button_tone_off
        if not settings_dict["power_saving_mode"]:
            arr[1] |= power_saving_mode_off

        long_duration = watch_info.longLightDuration if watch_info.longLightDuration else "4s"
        if settings_dict["light_duration"] == long_duration:
            arr[2] = 1
        # arr[3], arr[4], arr[5], ... left as 0 — date_format/language/auto_light
        # bits don't apply to this model, matching what's observed on the wire.

        return bytes(arr)

    @staticmethod
    def decode(setting_bytes: bytes) -> dict[str, object]:
        mask_24_hours = 0b00000001
        mask_button_tone_off = 0b00000010
        mask_light_off = 0b00000100
        power_saving_mode = 0b00010000

        setting_array = to_int_array(to_hex_string(setting_bytes))

        decoded: dict[str, object] = {}
        if setting_array[1] & mask_24_hours != 0:
            decoded["time_format"] = "24h"
        else:
            decoded["time_format"] = "12h"

        decoded["button_tone"] = (setting_array[1] & mask_button_tone_off) == 0
        decoded["auto_light"] = (setting_array[1] & mask_light_off) == 0
        decoded["power_saving_mode"] = (setting_array[1] & power_saving_mode) == 0
        decoded["date_format"] = "DD:MM" if setting_array[4] == 1 else "MM:DD"

        languages = ["English", "Spanish", "French", "German", "Italian", "Russian"]
        if 0 <= setting_array[5] < len(languages):
            decoded["language"] = languages[setting_array[5]]
        else:
            decoded["language"] = "English"

        long_duration = watch_info.longLightDuration if watch_info.longLightDuration else "4s"
        short_duration = watch_info.shortLightDuration if watch_info.shortLightDuration else "2s"
        decoded["light_duration"] = long_duration if setting_array[2] == 1 else short_duration
        return decoded

    @staticmethod
    def decode_mtg_b3000(setting_bytes: bytes) -> dict[str, object]:
        """
        Only surfaces the fields that actually apply to this model.
        Wire layout is identical to decode() — only the returned dict differs.
        """
        mask_button_tone_off = 0b00000010
        power_saving_mode = 0b00010000

        setting_array = to_int_array(to_hex_string(setting_bytes))

        decoded: dict[str, object] = {}
        decoded["button_tone"] = (setting_array[1] & mask_button_tone_off) == 0
        decoded["power_saving_mode"] = (setting_array[1] & power_saving_mode) == 0

        long_duration = watch_info.longLightDuration if watch_info.longLightDuration else "4s"
        short_duration = watch_info.shortLightDuration if watch_info.shortLightDuration else "2s"
        decoded["light_duration"] = long_duration if setting_array[2] == 1 else short_duration
        return decoded

    @staticmethod
    def prepare_watch_commands() -> list[BLEAction]:
        return [
            Write(
                handle=0x000C,
                data=bytes([Protocol.SETTING_FOR_BASIC.value])
            )
        ]

    @staticmethod
    def prepare_watch_commands_set(message_json: str) -> list[BLEAction]:
        json_setting: SettingsDict = json.loads(message_json).get("value")  # type: ignore
        encoded_setting = SettingsIOFunctional.encode(json_setting)
        return [Write(handle=0x000E, data=encoded_setting)]

    @staticmethod
    def prepare_watch_commands_set_mtg_b3000(message_json: str) -> list[BLEAction]:
        json_setting: MtgB3000SettingsDict = json.loads(message_json).get("value")  # type: ignore
        encoded_setting = SettingsIOFunctional.encode_mtg_b3000(json_setting)
        return [Write(handle=0x000E, data=encoded_setting)]


class SettingsIO:
    """
    Stateful backward-compatible wrapper.
    Acts as the interpreter for SettingsIOFunctional commands.
    """
    result: CancelableResult[str] | None = None
    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol) -> CancelableResult[str]:
        SettingsIO.connection = connection
        await connection.request(f"{Protocol.SETTING_FOR_BASIC.value:02X}")
        SettingsIO.result = CancelableResult[str]()
        return await SettingsIO.result.get_result()

    @staticmethod
    async def send_to_watch(_message: str) -> None:
        if SettingsIO.connection is None:
            raise RuntimeError("SettingsIO.connection is not set")

        commands = SettingsIOFunctional.prepare_watch_commands()
        for command in commands:
            if isinstance(command, Write):
                await SettingsIO.connection.write(command.handle, command.data)

    @staticmethod
    async def send_to_watch_set(message: str) -> None:
        if SettingsIO.connection is None:
            raise RuntimeError("SettingsIO.connection is not set")

        if watch_info.model == WatchModel.MTG_B3000:
            commands = SettingsIOFunctional.prepare_watch_commands_set_mtg_b3000(message)
        else:
            commands = SettingsIOFunctional.prepare_watch_commands_set(message)

        for command in commands:
            if isinstance(command, Write):
                setting_to_set = to_compact_string(to_hex_string(command.data))
                await SettingsIO.connection.write(command.handle, setting_to_set)

    @staticmethod
    def on_received(message: bytes) -> None:
        logger.info(f"SettingsIO onReceived: {message}")

        if watch_info.model == WatchModel.MTG_B3000:
            decoded_dict = SettingsIOFunctional.decode_mtg_b3000(message)
            settings.button_tone = decoded_dict["button_tone"]  # type: ignore
            settings.power_saving_mode = decoded_dict["power_saving_mode"]  # type: ignore
            settings.light_duration = decoded_dict["light_duration"]  # type: ignore
        else:
            decoded_dict = SettingsIOFunctional.decode(message)
            settings.time_format = decoded_dict["time_format"]  # type: ignore
            settings.button_tone = decoded_dict["button_tone"]  # type: ignore
            settings.auto_light = decoded_dict["auto_light"]  # type: ignore
            settings.power_saving_mode = decoded_dict["power_saving_mode"]  # type: ignore
            settings.date_format = decoded_dict["date_format"]  # type: ignore
            settings.language = decoded_dict["language"]  # type: ignore
            settings.light_duration = decoded_dict["light_duration"]  # type: ignore

        if SettingsIO.result is None:
            raise RuntimeError("SettingsIO.result is not set")
        SettingsIO.result.set_result(json.dumps(settings.__dict__))
        