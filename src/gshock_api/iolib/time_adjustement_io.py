from typing import Literal, TypedDict
import json

from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.iolib.error_io import ErrorIO
from gshock_api.logger import logger
from gshock_api.utils import to_compact_string, to_hex_string, to_int_array
from gshock_api.iolib.packet import Header, Payload, Protocol


CHARACTERISTICS: dict[str, int] = CasioConstants.CHARACTERISTICS


class TimeAdjustmentValueDict(TypedDict):
    timeAdjustment: Literal["True", "False"]
    minutesAfterHour: str


class TimeAdjustmentIO:
    result: CancelableResult[dict[str, object]] | None = None
    connection: ConnectionProtocol | None = None
    original_value: str | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol) -> CancelableResult[dict[str, object]]:
        TimeAdjustmentIO.connection = connection
        # 11 is SETTING_FOR_BLE in CasioConstants
        await connection.request(f"{Protocol.SETTING_FOR_BLE.value:02X}")
        TimeAdjustmentIO.result = CancelableResult[dict[str, object]]()
        return await TimeAdjustmentIO.result.get_result()

    @staticmethod
    def send_to_watch(message: str) -> None:
        if TimeAdjustmentIO.connection is None:
            raise RuntimeError("TimeAdjustmentIO.connection is not set")
        
        # Original code used "TIME_ADJUSTMENT" which seems to be 0x11 (Same as SETTING_FOR_BLE)
        # Assuming Protocol.SETTING_FOR_BLE is correct
        header = Header(Protocol.SETTING_FOR_BLE, size=1)
        TimeAdjustmentIO.connection.write(
            0x000C, bytearray([header.protocol.value])
        )

    @staticmethod
    async def send_to_watch_set(message: str) -> dict[str, str] | None:
        if TimeAdjustmentIO.original_value is None:
            return await ErrorIO.request("Error: Must call get before set")

        parsed_message = json.loads(message)
        time_adjustment: bool = parsed_message.get("timeAdjustment") == "True"
        minutes_after_hour: int = int(parsed_message.get("minutesAfterHour", "0"))

        def encode_time_adjustment(time_adjustment_val: bool, minutes_after_hour_val: int) -> bytes:
            raw_string = TimeAdjustmentIO.original_value
            # Example original string: "0x11 0F 0F 0F 06 00 00 00 00 00 01 00 80 30 30"
            int_array = to_int_array(raw_string)
            int_array[12] = 0x80 if not time_adjustment_val else 0x00
            int_array[13] = minutes_after_hour_val
            return bytes(int_array)

        encoded_time_adj = encode_time_adjustment(time_adjustment, minutes_after_hour)
        
        # Verify it starts with Protocol.SETTING_FOR_BLE (0x11)
        if encoded_time_adj[0] != Protocol.SETTING_FOR_BLE.value:
            # Maybe log or warn? For now proceed.
            pass
            
        payload = Payload(data=bytearray(encoded_time_adj[1:]))
        packet_bytes = bytearray([Protocol.SETTING_FOR_BLE.value]) + payload.data

        write_cmd = to_compact_string(to_hex_string(packet_bytes))
        if TimeAdjustmentIO.connection is None:
            raise RuntimeError("TimeAdjustmentIO.connection is not set")
        await TimeAdjustmentIO.connection.write(0x000E, write_cmd)
        return None

    @staticmethod
    def on_received(message: bytes) -> None:
        TimeAdjustmentIO.original_value = to_hex_string(message)  # save original message

        def is_time_adjustment_set(data: bytes) -> bool:
            # syncing off example: 110f0f0f0600500004000100->80<-10d2
            return int(data[12]) == 0x00

        def get_minutes_after_hour(data: bytes) -> int:
            # syncing off example: 110f0f0f060050000400010080->10<-d2
            return int(data[13])

        time_adjusted = is_time_adjustment_set(message)
        minutes_after_hour = get_minutes_after_hour(message)
        value_to_set_str = {
            "timeAdjusment": str(time_adjusted),
            "minutesAfterHour": str(minutes_after_hour),
        }

        if TimeAdjustmentIO.result is None:
            raise RuntimeError("TimeAdjustmentIO.result is not set")
        TimeAdjustmentIO.result.set_result(value_to_set_str)

    @staticmethod
    async def on_received_set(message: bytes) -> None:
        logger.info(f"TimeAdjustmentIO onReceivedSet: {message}")
