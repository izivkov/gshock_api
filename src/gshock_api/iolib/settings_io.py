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
from gshock_api.pending_requests_registry import PendingRequestsRegistry

CHARACTERISTICS: dict[str, int] = CasioConstants.CHARACTERISTICS


class SettingsDict(TypedDict):
    time_format: Literal["24h", "12h"]
    button_tone: bool
    auto_light: bool
    power_saving_mode: bool
    light_duration: Literal["4s", "2s"]
    date_format: Literal["DD:MM", "MM:DD"]
    language: Literal["English", "Spanish", "French", "German", "Italian", "Russian"]


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

        if settings_dict["light_duration"] == "4s":
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

        decoded["light_duration"] = "4s" if setting_array[2] == 1 else "2s"
        return decoded

    @staticmethod
    def prepare_watch_commands() -> list[BLEAction]:
        return [
            Write(
                handle=CasioConstants.HANDLE_READ_ALL_FEATURES,
                data=bytes([Protocol.SETTING_FOR_BASIC.value])
            )
        ]

    @staticmethod
    def prepare_watch_commands_set(message_json: str) -> list[BLEAction]:
        json_setting: SettingsDict = json.loads(message_json).get("value")  # type: ignore
        encoded_setting = SettingsIOFunctional.encode(json_setting)
        return [Write(handle=CasioConstants.HANDLE_ALL_FEATURES_WRITE, data=encoded_setting)]


class SettingsIO:
    """
    Stateful backward-compatible wrapper.
    Acts as the interpreter for SettingsIOFunctional commands.
    """
    result: CancelableResult[str] | None = None
    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol) -> str:
        SettingsIO.connection = connection
        await connection.request(f"{Protocol.SETTING_FOR_BASIC.value:02X}")
        SettingsIO.result = CancelableResult[str]()
        # Register the pending request
        PendingRequestsRegistry.register("SettingsIO", SettingsIO.result)
        try:
            return await SettingsIO.result.get_result()
        finally:
            # Unregister when complete (success or error)
            PendingRequestsRegistry.unregister("SettingsIO")

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

        commands = SettingsIOFunctional.prepare_watch_commands_set(message)
        for command in commands:
            if isinstance(command, Write):
                setting_to_set = to_compact_string(to_hex_string(command.data))
                await SettingsIO.connection.write(command.handle, setting_to_set)

    @staticmethod
    def on_received(message: bytes) -> None:
        logger.info(f"SettingsIO onReceived: {message}")

        decoded_dict = SettingsIOFunctional.decode(message)
        
        # Keep global settings singleton synchronized for compatibility
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