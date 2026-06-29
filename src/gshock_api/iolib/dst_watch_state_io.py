from enum import IntEnum

from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.iolib.actions import BLEAction, Write
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.iolib.packet import Protocol
from gshock_api.pending_requests_registry import PendingRequestsRegistry

CHARACTERISTICS: dict[str, int] = CasioConstants.CHARACTERISTICS


class DtsState(IntEnum):
    ZERO = 0
    TWO = 2
    FOUR = 4


class DstWatchStateIOFunctional:
    """
    Pure functional DST watch state modules implementing Monoids.
    """

    @staticmethod
    def prepare_watch_commands() -> list[BLEAction]:
        return [
            Write(
                handle=CasioConstants.HANDLE_READ_ALL_FEATURES,
                data=bytes([Protocol.DST_WATCH_STATE.value])
            )
        ]


class DstWatchStateIO:
    """
    Stateful backward-compatible wrapper.
    Acts as the interpreter for DstWatchStateIOFunctional commands.
    """
    result: CancelableResult[bytes] | None = None
    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol, state: DtsState) -> bytes:
        DstWatchStateIO.connection = connection
        key = f"{Protocol.DST_WATCH_STATE.value:02x}0{state.value}"
        await connection.request(key)
        DstWatchStateIO.result = CancelableResult[bytes]()
        # Register the pending request with unique name based on state
        PendingRequestsRegistry.register(f"DstWatchStateIO_{state.value}", DstWatchStateIO.result)
        try:
            return await DstWatchStateIO.result.get_result()
        finally:
            # Unregister when complete (success or error)
            PendingRequestsRegistry.unregister(f"DstWatchStateIO_{state.value}")

    @staticmethod
    async def send_to_watch(_message: str = "") -> None:
        if DstWatchStateIO.connection is None:
            raise RuntimeError("DstWatchStateIO.connection is not set")

        commands = DstWatchStateIOFunctional.prepare_watch_commands()
        for command in commands:
            if isinstance(command, Write):
                await DstWatchStateIO.connection.write(command.handle, command.data)

    @staticmethod
    def on_received(data: bytes) -> None:
        if DstWatchStateIO.result is None:
            raise RuntimeError("DstWatchStateIO.result is not set")
        DstWatchStateIO.result.set_result(data)
