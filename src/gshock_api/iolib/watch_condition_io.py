from typing import TypedDict
import json

from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.watch_info import watch_info
from gshock_api.iolib.packet import Header, Payload, Protocol

CHARACTERISTICS: dict[str, int] = CasioConstants.CHARACTERISTICS


class WatchConditionValue(TypedDict):
    battery_level_percent: int
    temperature: int


class WatchConditionIO:
    result: CancelableResult | None = None
    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol) -> CancelableResult[dict[str, int]]:
        WatchConditionIO.connection = connection
        await connection.request(f"{Protocol.WATCH_CONDITION.value:02X}")
        WatchConditionIO.result = CancelableResult[dict[str, int]]()
        return await WatchConditionIO.result.get_result()

    @staticmethod
    async def send_to_watch(connection: ConnectionProtocol) -> None:
        header = Header(Protocol.WATCH_CONDITION, size=1)
        await connection.write(0x000C, bytearray([header.protocol.value]))

    @staticmethod
    def on_received(data: bytes) -> None:
        def decode_value(data_bytes: bytes) -> WatchConditionValue:
            # Assuming data starts with Protocol (Header) or is just payload?
            # Original code: int_arr = list(map(int, data_str))
            # bytes_data = bytes(int_arr[1:]) -> skipped index 0. Index 0 is protocol.
            
            # Using data as bytes directly
            if len(data_bytes) < 3: # Protocol + 2 bytes
                return {"battery_level_percent": 0, "temperature": 0}

            header = Header(Protocol(data_bytes[0]), size=len(data_bytes))
            # Payload starts at 1
            payload = Payload(data=bytearray(data_bytes[1:]))
            
            bytes_data = payload.data

            if len(bytes_data) >= 2:
                battery_level_lower_limit = watch_info.batteryLevelLowerLimit
                battery_level_upper_limit = watch_info.batteryLevelUpperLimit

                multiplier = round(
                    100.0 / (battery_level_upper_limit - battery_level_lower_limit)
                )
                battery_level = int(bytes_data[0]) - battery_level_lower_limit
                battery_level_percent = min(max(battery_level * multiplier, 0), 100)
                temperature = int(bytes_data[1])

                return {
                    "battery_level_percent": battery_level_percent,
                    "temperature": temperature,
                }
            return {"battery_level_percent": 0, "temperature": 0}
        
        # If input was string in original, we need to handle bytes now.
        # Assuming caller passes bytes. 
        # But wait, original signature was `data: str`.
        # I changed it to `data: bytes` in signature.
        if WatchConditionIO.result is None:
            raise RuntimeError("WatchConditionIO.result is not set")
        WatchConditionIO.result.set_result(decode_value(data))
