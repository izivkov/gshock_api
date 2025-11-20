from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants

CHARACTERISTICS = CasioConstants.CHARACTERISTICS

class DstForWorldCitiesIO:
    result: CancelableResult = None
    connection = None

    @staticmethod
    async def request(connection, city_number: int):
        DstForWorldCitiesIO.connection = connection
        key = f"1e0{city_number}"
        await connection.request(key)

        DstForWorldCitiesIO.result = CancelableResult()
        return DstForWorldCitiesIO.result.get_result()

    @staticmethod
    async def send_to_watch(connection) -> None:
        connection.write(0x000C, bytearray([CHARACTERISTICS["CASIO_DST_SETTING"]]))

    @staticmethod
    def on_received(data) -> None:
        DstForWorldCitiesIO.result.set_result(data)
