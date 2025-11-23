import json
from typing import Protocol, TypedDict, Literal

from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.logger import logger
from gshock_api.settings import settings
from gshock_api.utils import to_compact_string, to_hex_string, to_int_array
from connection_protocol import ConnectionProtocol


CHARACTERISTICS: dict[str, int] = CasioConstants.CHARACTERISTICS


class SettingsDict(TypedDict):
    time_format: Literal["24h", "12h"]
    button_tone: bool
    auto_light: bool
    power_saving_mode: bool
    light_duration: Literal["4s", "2s"]
    date_format: Literal["DD:MM", "MM:DD"]
    language: Literal["English", "Spanish", "French", "German", "Italian", "Russian"]


class SettingsIO:
    result: CancelableResult[str] | None = None
    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol) -> CancelableResult[str]:
        SettingsIO.connection = connection
        await connection.request("13")
        SettingsIO.result = CancelableResult[str]()
        return await SettingsIO.result.get_result()

    @staticmethod
    def send_to_watch(message: str) -> None:
        if SettingsIO.connection is None:
            raise RuntimeError("SettingsIO.connection is not set")
        SettingsIO.connection.write(
            0x000C, bytearray([CHARACTERISTICS["CASIO_SETTING_FOR_BASIC"]])
        )

    @staticmethod
    async def send_to_watch_set(message: str) -> None:
        def encode(settings: SettingsDict) -> bytearray:
            mask_24_hours = 0b00000001
            MASK_BUTTON_TONE_OFF = 0b00000010
            MASK_LIGHT_OFF = 0b00000100
            POWER_SAVING_MODE = 0b00010000

            arr = bytearray(12)
            arr[0] = CHARACTERISTICS["CASIO_SETTING_FOR_BASIC"]
            if settings["time_format"] == "24h":
                arr[1] |= mask_24_hours
            if not settings["button_tone"]:
                arr[1] |= MASK_BUTTON_TONE_OFF
            if not settings["auto_light"]:
                arr[1] |= MASK_LIGHT_OFF
            if not settings["power_saving_mode"]:
                arr[1] |= POWER_SAVING_MODE

            if settings["light_duration"] == "4s":
                arr[2] = 1
            if settings["date_format"] == "DD:MM":
                arr[4] = 1

            language_index = {
                "English": 0,
                "Spanish": 1,
                "French": 2,
                "German": 3,
                "Italian": 4,
                "Russian": 5,
            }
            arr[5] = language_index.get(settings["language"], 0)

            return arr

        json_setting: SettingsDict = json.loads(message).get("value")  # type: ignore
        if SettingsIO.connection
