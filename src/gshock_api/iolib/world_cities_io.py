from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.iolib.packet import Header, Protocol
from gshock_api.pending_requests_registry import PendingRequestsRegistry

CHARACTERISTICS: dict[str, int] = CasioConstants.CHARACTERISTICS


class WorldCitiesIO:
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
        header = Header(Protocol.WORLD_CITIES, size=1)
        await connection.write(0x000C, bytearray([header.protocol.value]))

    @staticmethod
    def on_received(data: bytes) -> None:
        if WorldCitiesIO.result is None:
            raise RuntimeError("WorldCitiesIO.result is not set")
        WorldCitiesIO.result.set_result(data)
