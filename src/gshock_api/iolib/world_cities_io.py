from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants

CHARACTERISTICS = CasioConstants.CHARACTERISTICS


class WorldCitiesIO:
    result: CancelableResult = None
    connection = None

    @staticmethod
    async def request(connection, cityNumber: int):
        WorldCitiesIO.connection = connection
        key = f"1f0{cityNumber}"

        await connection.request(key)

        WorldCitiesIO.result = CancelableResult()
        return WorldCitiesIO.result.get_result()

    @staticmethod
    async def send_to_watch(connection) -> None:
        connection.write(0x000C, bytearray([CHARACTERISTICS["CASIO_WORLD_CITIES"]]))

    @staticmethod
    def on_received(data) -> None:
        WorldCitiesIO.result.set_result(data)
