from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.iolib.actions import BLEAction, Write
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.iolib.packet import Protocol
from gshock_api.pending_requests_registry import PendingRequestsRegistry


class DstForWorldCitiesIOFunctional:
    """
    Pure functional DST for world cities modules implementing Monoids.
    """

    @staticmethod
    def prepare_watch_commands() -> list[BLEAction]:
        return [
            Write(
                handle=CasioConstants.HANDLE_READ_ALL_FEATURES,
                data=bytes([Protocol.DST_SETTING.value])
            )
        ]


class DstForWorldCitiesIO:
    """
    Stateful backward-compatible wrapper.
    Acts as the interpreter for DstForWorldCitiesIOFunctional commands.
    """
    result: CancelableResult[bytes] | None = None
    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol, city_number: int) -> bytes:
        DstForWorldCitiesIO.connection = connection
        key = f"{Protocol.DST_SETTING.value:02x}0{city_number}"
        await connection.request(key)

        DstForWorldCitiesIO.result = CancelableResult[bytes]()
        # Register the pending request with unique name based on city number
        PendingRequestsRegistry.register(f"DstForWorldCitiesIO_{city_number}", DstForWorldCitiesIO.result)
        try:
            return await DstForWorldCitiesIO.result.get_result()
        finally:
            # Unregister when complete (success or error)
            PendingRequestsRegistry.unregister(f"DstForWorldCitiesIO_{city_number}")

    @staticmethod
    async def send_to_watch(_message: str = "") -> None:
        if DstForWorldCitiesIO.connection is None:
            raise RuntimeError("DstForWorldCitiesIO.connection is not set")

        commands = DstForWorldCitiesIOFunctional.prepare_watch_commands()
        for command in commands:
            if isinstance(command, Write):
                await DstForWorldCitiesIO.connection.write(command.handle, command.data)

    @staticmethod
    def on_received(data: bytes) -> None:
        if DstForWorldCitiesIO.result is None:
            raise RuntimeError("DstForWorldCitiesIO.result is not set")
        DstForWorldCitiesIO.result.set_result(data)
