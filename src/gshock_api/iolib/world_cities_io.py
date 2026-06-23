from gshock_api.cancelable_result import CancelableResult
from gshock_api.iolib.actions import BLEAction, Write
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.iolib.packet import Protocol
from gshock_api.pending_requests_registry import PendingRequestsRegistry

class WorldCitiesIOFunctional:
    """
    Pure functional world cities modules implementing Monoids.
    """

    @staticmethod
    def prepare_watch_commands() -> list[BLEAction]:
        return [
            Write(
                handle=0x000C,
                data=bytes([Protocol.WORLD_CITIES.value])
            )
        ]


class WorldCitiesIO:
    """
    Stateful backward-compatible wrapper.
    Acts as the interpreter for WorldCitiesIOFunctional commands.
    """
    result: CancelableResult[bytes] | None = None
    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol, city_number: int) -> CancelableResult[bytes]:
        WorldCitiesIO.connection = connection
        key = f"{Protocol.WORLD_CITIES.value:02X}0{city_number}"
        await connection.request(key)

        WorldCitiesIO.result = CancelableResult[bytes]()
        # Register the pending request with unique name based on city number
        PendingRequestsRegistry.register(f"WorldCitiesIO_{city_number}", WorldCitiesIO.result)
        try:
            return await WorldCitiesIO.result.get_result()
        finally:
            # Unregister when complete (success or error)
            PendingRequestsRegistry.unregister(f"WorldCitiesIO_{city_number}")

    @staticmethod
    async def send_to_watch(connection: ConnectionProtocol) -> None:
        commands = WorldCitiesIOFunctional.prepare_watch_commands()
        for command in commands:
            if isinstance(command, Write):
                await connection.write(command.handle, command.data)

    @staticmethod
    def on_received(data: bytes) -> None:
        if WorldCitiesIO.result is None:
            raise RuntimeError("WorldCitiesIO.result is not set")
        WorldCitiesIO.result.set_result(data)
