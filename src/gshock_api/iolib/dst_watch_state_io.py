from enum import IntEnum

from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.iolib.connection_protocol import ConnectionProtocol

CHARACTERISTICS: dict[str, int] = CasioConstants.CHARACTERISTICS


class DtsState(IntEnum):
    ZERO = 0
    TWO = 2
    FOUR = 4


class DstWatchStateIO:
    result: CancelableResult[bytes] | None = None
    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol, state: DtsState) -> CancelableResult[bytes]:
        DstWatchStateIO.connection = connection
        key = f"1d0{state.value}"
        await connection.request(key)
        DstWatchStateIO.result = CancelableResult[bytes]()
        return await DstWatchStateIO.result.get_result()

    @staticmethod
    async def send_to_watch(connection: ConnectionProtocol) -> None:
        await connection.write(0x000C, bytearray([CHARACTERISTICS["CASIO_DST_WATCH_STATE"]]))

    @staticmethod
    def on_received(data: bytes) -> None:
        if DstWatchStateIO.result is None:
            raise RuntimeError("DstWatchStateIO.result is not set")
        DstWatchStateIO.result.set_result(data)
