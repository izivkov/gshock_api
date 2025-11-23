from typing import TypedDict

from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.watch_info import watch_info

CHARACTERISTICS: dict[str, int] = CasioConstants.CHARACTERISTICS


class WatchConditionValue(TypedDict):
    battery_level_percent: int
    temperature: int


class WatchConditionIO:
    result: CancelableResult | None = None
    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol) -> CancelableResult:
        WatchConditionIO.connection = connection
        await connection.request("28")
        WatchConditionIO.result = CancelableResult()
        return await WatchConditionIO.result.get_result()

    @staticmethod
    async def send_to_watch(connection: ConnectionProtocol) -> None:
        connection.write(0x000C, bytearray([CHARACTERISTICS["CASIO_WATCH_CONDITION"]]))

    @staticmethod
    def on_received(data: str) -> None:
        def decode_value(data_str: str) -> WatchConditionValue:
            int_arr = list(map(int, data_str))
            bytes_data = bytes(int_arr[1:])

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

        if WatchConditionIO.result is None:
            raise RuntimeError("WatchConditionIO.result is not set")
        WatchConditionIO.result.set_result(decode_value(data))
