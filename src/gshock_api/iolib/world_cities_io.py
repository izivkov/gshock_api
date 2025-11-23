from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.iolib.connection_protocol import ConnectionProtocol

CHARACTERISTICS: dict[str, int] = CasioConstants.CHARACTERISTICS


class WorldCitiesIO:
    result: CancelableResult[bytes] | None = None
    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol, cityNumber: int) -> CancelableResult[bytes]:
        WorldCitiesIO.connection = connection
        key = f"1f0{cityNumber}"
        await connection.request(key)

        WorldCitiesIO.result = CancelableResult[bytes]()
        return await WorldCitiesIO.result.get_result()

    @staticmethod
    async def send_to_watch(connection: ConnectionProtocol) -> None:
        connection.write(0x000C, bytearray([CHARACTERISTICS["CASIO_WORLD_CITIES"]]))

    @staticmethod
    def on_received(data: bytes) -> None:
        if WorldCitiesIO.result is None:
            raise RuntimeError("WorldCitiesIO.result is not set")
        WorldCitiesIO.result.set_result(data)
