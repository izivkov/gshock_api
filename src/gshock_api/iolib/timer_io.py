import json

from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.utils import to_compact_string, to_hex_string
from gshock_api.iolib.packet import Header, Payload, Protocol

CHARACTERISTICS: dict[str, int] = CasioConstants.CHARACTERISTICS


class TimerIO:
    result: CancelableResult | None = None
    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol) -> CancelableResult:
        TimerIO.connection = connection
        await connection.request(f"{Protocol.TIMER.value:02X}")
        TimerIO.result = CancelableResult()
        return await TimerIO.result.get_result()

    @staticmethod
    async def send_to_watch(connection: ConnectionProtocol) -> None:
        header = Header(Protocol.TIMER, size=1)
        await connection.write(0x000C, bytearray([header.protocol.value]))

    @staticmethod
    async def send_to_watch_set(data: str) -> None:
        def encode(seconds_str: str) -> bytearray:
            in_seconds = int(seconds_str)
            hours = in_seconds // 3600
            minutes_and_seconds = in_seconds % 3600
            minutes = minutes_and_seconds // 60
            seconds = minutes_and_seconds % 60

            arr = bytearray(6)
            # arr[0] was 0x18. We return payload (time part)
            arr[0] = hours
            arr[1] = minutes
            arr[2] = seconds
            return arr

        data_obj = json.loads(data)
        seconds_as_byte_arr = encode(data_obj.get("value", "0"))
        
        # Header + Payload
        payload = Payload(data=seconds_as_byte_arr)
        packet_bytes = bytearray([Protocol.TIMER.value]) + payload.data
        
        seconds_as_compact_str = to_compact_string(to_hex_string(packet_bytes))
        if TimerIO.connection is None:
            raise RuntimeError("TimerIO.connection is not set")
        await TimerIO.connection.write(0x000E, seconds_as_compact_str)

    @staticmethod
    def on_received(data: list[int]) -> None:
        def decode_value(data_list: list[int]) -> int:
            # data_list includes protocol at index 0?
            # Original code: hours=data_list[1], mins=data_list[2]
            # If data is full packet bytes converted to int list
            header_offset = 1
            if len(data_list) < 4:
                return 0
            
            hours = data_list[0 + header_offset]
            minutes = data_list[1 + header_offset]
            seconds = data_list[2 + header_offset]
            return hours * 3600 + minutes * 60 + seconds

        decoded = decode_value(data)
        if TimerIO.result is None:
            raise RuntimeError("TimerIO.result is not set")
        TimerIO.result.set_result(decoded)
