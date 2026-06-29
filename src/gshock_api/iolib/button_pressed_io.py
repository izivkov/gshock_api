from enum import IntEnum

from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.iolib.actions import BLEAction, Write
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.iolib.packet import Header, Payload, Protocol
from gshock_api.pending_requests_registry import PendingRequestsRegistry


class WatchButton(IntEnum):
    UPPER_LEFT = 1
    LOWER_LEFT = 2
    UPPER_RIGHT = 3
    LOWER_RIGHT = 4
    NO_BUTTON = 5
    INVALID = 6
    FIND = 7


class ButtonPressedIOFunctional:
    """
    Pure functional button pressed modules implementing Monoids.
    """

    @staticmethod
    def decode(data_bytes: bytes) -> WatchButton:
        default_button = WatchButton.INVALID

        if len(data_bytes) < 19:
            return default_button

        try:
            header = Header(Protocol(data_bytes[0]), size=len(data_bytes))
            if header.protocol != Protocol.BLE_FEATURES:
                return default_button

            payload = Payload(bytearray(data_bytes[1:]))
            button_indicator = payload.data[7]
        except (ValueError, IndexError):
            return default_button

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

    @staticmethod
    def prepare_watch_commands() -> list[BLEAction]:
        return [
            Write(
                handle=CasioConstants.HANDLE_READ_ALL_FEATURES,
                data=bytes([Protocol.BLE_FEATURES.value])
            )
        ]

    @staticmethod
    def prepare_watch_commands_set(data: bytes | str) -> list[BLEAction]:
        data_bytes = data if isinstance(data, bytes) else data.encode("utf-8")
        return [Write(handle=CasioConstants.HANDLE_ALL_FEATURES_WRITE, data=data_bytes)]


class ButtonPressedIO:
    """
    Stateful backward-compatible wrapper.
    Acts as the interpreter for ButtonPressedIOFunctional commands.
    """
    result: CancelableResult[WatchButton] | None = None
    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol) -> WatchButton:
        ButtonPressedIO.connection = connection
        await connection.request(f"{Protocol.BLE_FEATURES.value:02X}")
        ButtonPressedIO.result = CancelableResult[WatchButton]()
        # Register the pending request
        PendingRequestsRegistry.register("ButtonPressedIO", ButtonPressedIO.result)
        try:
            return await ButtonPressedIO.result.get_result()
        finally:
            # Unregister when complete (success or error)
            PendingRequestsRegistry.unregister("ButtonPressedIO")

    @staticmethod
    async def send_to_watch(_message: str = "") -> None:
        if ButtonPressedIO.connection is None:
            raise RuntimeError("ButtonPressedIO.connection is not set")

        commands = ButtonPressedIOFunctional.prepare_watch_commands()
        for command in commands:
            if isinstance(command, Write):
                await ButtonPressedIO.connection.write(command.handle, command.data)

    @staticmethod
    async def send_to_watch_set(data: bytes | str) -> None:
        if ButtonPressedIO.connection is None:
            raise RuntimeError("ButtonPressedIO.connection is not set")

        commands = ButtonPressedIOFunctional.prepare_watch_commands_set(data)
        for command in commands:
            if isinstance(command, Write):
                await ButtonPressedIO.connection.write(command.handle, command.data)

    @staticmethod
    def on_received(data: bytes) -> None:
        button = ButtonPressedIOFunctional.decode(data)
        if ButtonPressedIO.result is None:
            raise RuntimeError("ButtonPressedIO.result is not set")
        ButtonPressedIO.result.set_result(button)
