from typing import TypedDict

from gshock_api.cancelable_result import CancelableResult
from gshock_api.iolib.actions import BLEAction, Write
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.iolib.packet import Header, Payload, Protocol
from gshock_api.watch_info import watch_info
from gshock_api.pending_requests_registry import PendingRequestsRegistry

CHARACTERISTICS: dict[str, int] = CasioConstants.CHARACTERISTICS

class WatchConditionValue(TypedDict):
    battery_level_percent: int
    temperature: int


class WatchConditionIOFunctional:
    """
    Pure functional watch condition modules implementing Monoids.
    """

    @staticmethod
    def decode(data_bytes: bytes) -> WatchConditionValue:
        min_bytes_len = 3
        if len(data_bytes) < min_bytes_len:
            return {"battery_level_percent": 0, "temperature": 0}

        try:
            header = Header(Protocol(data_bytes[0]), size=len(data_bytes))
            if header.protocol != Protocol.WATCH_CONDITION:
                return {"battery_level_percent": 0, "temperature": 0}

            payload = Payload(data=bytearray(data_bytes[1:]))
            bytes_data = payload.data
        except (ValueError, IndexError):
            return {"battery_level_percent": 0, "temperature": 0}

        min_payload_len = 2
        if len(bytes_data) >= min_payload_len:
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

    @staticmethod
    def prepare_watch_commands() -> list[BLEAction]:
        return [
            Write(
                handle=0x000C,
                data=bytes([Protocol.WATCH_CONDITION.value])
            )
        ]


class WatchConditionIO:
    """
    Stateful backward-compatible wrapper.
    Acts as the interpreter for WatchConditionIOFunctional commands.
    """
    result: CancelableResult | None = None
    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol) -> CancelableResult[dict[str, int]]:
        WatchConditionIO.connection = connection
        await connection.request(f"{Protocol.WATCH_CONDITION.value:02X}")
        WatchConditionIO.result = CancelableResult[dict[str, int]]()
        # Register the pending request
        PendingRequestsRegistry.register("WatchConditionIO", WatchConditionIO.result)
        try:
            return await WatchConditionIO.result.get_result()
        finally:
            # Unregister when complete (success or error)
            PendingRequestsRegistry.unregister("WatchConditionIO")

    @staticmethod
    async def send_to_watch(connection: ConnectionProtocol) -> None:
        commands = WatchConditionIOFunctional.prepare_watch_commands()
        for command in commands:
            if isinstance(command, Write):
                await connection.write(command.handle, command.data)

    @staticmethod
    def on_received(data: bytes) -> None:
        decoded = WatchConditionIOFunctional.decode(data)
        if WatchConditionIO.result is None:
            raise RuntimeError("WatchConditionIO.result is not set")
        WatchConditionIO.result.set_result(decoded)  # type: ignore[arg-type]
