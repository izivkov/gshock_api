from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.iolib.packet import Header, Protocol

CHARACTERISTICS: dict[str, int] = CasioConstants.CHARACTERISTICS


class DstForWorldCitiesIO:
    result: CancelableResult = None
    connection = None

    @staticmethod
    async def request(connection: ConnectionProtocol, city_number: int) -> CancelableResult[bytes]:
        DstForWorldCitiesIO.connection = connection
        key = f"{Protocol.DST_SETTING.value:02x}0{city_number}"
        await connection.request(key)

        DstForWorldCitiesIO.result = CancelableResult()
        return await DstForWorldCitiesIO.result.get_result()

    @staticmethod
    async def send_to_watch(connection: ConnectionProtocol) -> None:
        header = Header(Protocol.DST_SETTING, size=1)
        await connection.write(0x000C, bytearray([header.protocol.value]))

    @staticmethod
    def on_received(data: bytes) -> None:
        if DstForWorldCitiesIO.result is None:
            raise RuntimeError("DstForWorldCitiesIO.result is not set")
        DstForWorldCitiesIO.result.set_result(data)
