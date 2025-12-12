from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.iolib.packet import Header, Protocol

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
        return await WorldCitiesIO.result.get_result()

    @staticmethod
    async def send_to_watch(connection: ConnectionProtocol) -> None:
        header = Header(Protocol.WORLD_CITIES, size=1)
        await connection.write(0x000C, bytearray([header.protocol.value]))

    @staticmethod
    def on_received(data: bytes) -> None:
        if WorldCitiesIO.result is None:
            raise RuntimeError("WorldCitiesIO.result is not set")
        WorldCitiesIO.result.set_result(data)
