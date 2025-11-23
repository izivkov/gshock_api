import json

from connection_protocol import ConnectionProtocol

from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.utils import to_compact_string, to_hex_string

CHARACTERISTICS: dict[str, int] = CasioConstants.CHARACTERISTICS


class TimerIO:
    result: CancelableResult[int] | None = None
    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol) -> CancelableResult[int]:
        TimerIO.connection = connection
        await connection.request("18")
        TimerIO.result = CancelableResult[int]()
        return await TimerIO.result.get_result()

    @staticmethod
    async def send_to_watch(connection: ConnectionProtocol) -> None:
        await connection.write(0x000C, bytearray([CHARACTERISTICS["CASIO_TIMER"]]))

    @staticmethod
    async def send_to_watch_set(data: str) -> None:
        def encode(seconds_str: str) -> bytearray:
            in_seconds = int(seconds_str)
            hours = in_seconds // 3600
            minutes_and_seconds = in_seconds % 3600
            minutes = minutes_and_seconds // 60
            seconds = minutes_and_seconds % 60

            arr = bytearray(7)
            arr[0] = 0x18
            arr[1] = hours
            arr[2] = minutes
            arr[3] = seconds
            return arr

        data_obj = json.loads(data)
        seconds_as_byte_arr = encode(data_obj.get("value", "0"))
        seconds_as_compact_str = to_compact_string(to_hex_string(seconds_as_byte_arr))
        if TimerIO.connection is None:
            raise RuntimeError("TimerIO.connection is not set")
        await TimerIO.connection.write(0x000E, seconds_as_compact_str)

    @staticmethod
    def on_received(data: list[int]) -> None:
        def decode_value(data_list: list[int]) -> int:
            hours = data_list[1]
            minutes = data_list[2]
            seconds = data_list[3]
            return hours * 3600 + minutes * 60 + seconds

        decoded = decode_value(data)
        if TimerIO.result is None:
            raise RuntimeError("TimerIO.result is not set")
        TimerIO.result.set_result(decoded)
