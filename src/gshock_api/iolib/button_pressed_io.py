from enum import IntEnum

from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.utils import to_hex_string, to_int_array

CHARACTERISTICS: dict[str, int] = CasioConstants.CHARACTERISTICS


class WatchButton(IntEnum):
    UPPER_LEFT = 1
    LOWER_LEFT = 2
    UPPER_RIGHT = 3
    LOWER_RIGHT = 4
    NO_BUTTON = 5
    INVALID = 6
    FIND = 7


class ButtonPressedIO:
    result: CancelableResult | None = None
    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol) -> CancelableResult:
        ButtonPressedIO.connection = connection
        await connection.request("10")
        ButtonPressedIO.result = CancelableResult()
        return await ButtonPressedIO.result.get_result()

    @staticmethod
    async def send_to_watch(connection: ConnectionProtocol) -> None:
        await connection.write(0x000C, bytearray([CHARACTERISTICS["CASIO_BLE_FEATURES"]]))

    @staticmethod
    async def send_to_watch_set(data: bytes | str) -> None:
        if ButtonPressedIO.connection is None:
            raise RuntimeError("ButtonPressedIO.connection is not set")
        await ButtonPressedIO.connection.write(0x000E, data)

    @staticmethod
    def on_received(data: bytes) -> None:

        def button_pressed_callback(data_bytes: bytes) -> WatchButton:
            """
            RIGHT BUTTON: 0x10 17 62 07 38 85 CD 7F ->04<- 03 0F FF FF FF FF 24 00 00 00
            LEFT BUTTON:  0x10 17 62 07 38 85 CD 7F ->01<- 03 0F FF FF FF FF 24 00 00 00
            RESET:        0x10 17 62 16 05 85 dd 7f ->00<- 03 0f ff ff ff ff 24 00 00 00 // after watch reset
            AUTO-TIME:    0x10 17 62 16 05 85 dd 7f ->03<- 03 0f ff ff ff ff 24 00 00 00 // no button pressed
            """
            default_button = WatchButton.INVALID
            if len(data_bytes) < 19:
                return default_button

            ble_int_arr = to_int_array(to_hex_string(data_bytes))
            button_indicator = ble_int_arr[8]

            class ButtonIndicatorCodes:
                RESET = 0
                LEFT_PRESS = 1
                FIND = 2
                NO_BUTTON = 3
                RIGHT_PRESS = 4

            button_map = {
                ButtonIndicatorCodes.RESET: WatchButton.LOWER_LEFT,
                ButtonIndicatorCodes.LEFT_PRESS: WatchButton.LOWER_LEFT,
                ButtonIndicatorCodes.FIND: WatchButton.FIND,
                ButtonIndicatorCodes.NO_BUTTON: WatchButton.NO_BUTTON,
                ButtonIndicatorCodes.RIGHT_PRESS: WatchButton.LOWER_RIGHT,
            }

            return button_map.get(button_indicator, WatchButton.LOWER_RIGHT)

        button = button_pressed_callback(data)
        if ButtonPressedIO.result is None:
            raise RuntimeError("ButtonPressedIO.result is not set")
        ButtonPressedIO.result.set_result(button)
