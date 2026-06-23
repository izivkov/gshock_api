import json

from gshock_api.cancelable_result import CancelableResult
from gshock_api.iolib.actions import BLEAction, Write
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.iolib.packet import Protocol
from gshock_api.utils import to_compact_string, to_hex_string
from gshock_api.pending_requests_registry import PendingRequestsRegistry


class TimerIOFunctional:
    """
    Pure functional timer modules implementing Monoids.
    """

    @staticmethod
    def encode(seconds: int) -> bytes:
        hours = seconds // 3600
        minutes_and_seconds = seconds % 3600
        minutes = minutes_and_seconds // 60
        secs = minutes_and_seconds % 60

        # Protocol.TIMER.value = 0x18, then 3 bytes for HMS, then 2 bytes padding/flags
        return bytes([Protocol.TIMER.value, hours, minutes, secs, 0, 0])

    @staticmethod
    def decode(data_bytes: bytes) -> int:
        header_offset = 1
        min_data_len = 4
        if len(data_bytes) < min_data_len:
            return 0

        hours = data_bytes[0 + header_offset]
        minutes = data_bytes[1 + header_offset]
        seconds = data_bytes[2 + header_offset]
        return hours * 3600 + minutes * 60 + seconds

    @staticmethod
    def prepare_watch_commands() -> list[BLEAction]:
        return [
            Write(
                handle=0x000C,
                data=bytes([Protocol.TIMER.value])
            )
        ]

    @staticmethod
    def prepare_watch_commands_set(message_json: str) -> list[BLEAction]:
        data_obj = json.loads(message_json)
        seconds = int(data_obj.get("value", 0))
        encoded = TimerIOFunctional.encode(seconds)
        return [Write(handle=0x000E, data=encoded)]


class TimerIO:
    """
    Stateful backward-compatible wrapper.
    Acts as the interpreter for TimerIOFunctional commands.
    """
    result: CancelableResult | None = None
    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol) -> CancelableResult:
        TimerIO.connection = connection
        await connection.request(f"{Protocol.TIMER.value:02X}")
        TimerIO.result = CancelableResult()
        # Register the pending request
        PendingRequestsRegistry.register("TimerIO", TimerIO.result)
        try:
            return await TimerIO.result.get_result()
        finally:
            # Unregister when complete (success or error)
            PendingRequestsRegistry.unregister("TimerIO")

    @staticmethod
    async def send_to_watch(connection: ConnectionProtocol) -> None:
        commands = TimerIOFunctional.prepare_watch_commands()
        for command in commands:
            if isinstance(command, Write):
                await connection.write(command.handle, command.data)

    @staticmethod
    async def send_to_watch_set(data: str) -> None:
        if TimerIO.connection is None:
            raise RuntimeError("TimerIO.connection is not set")

        commands = TimerIOFunctional.prepare_watch_commands_set(data)
        for command in commands:
            if isinstance(command, Write):
                seconds_as_compact_str = to_compact_string(to_hex_string(command.data))
                await TimerIO.connection.write(0x000E, seconds_as_compact_str)

    @staticmethod
    def on_received(data: bytes) -> None:
        decoded = TimerIOFunctional.decode(data)
        if TimerIO.result is None:
            raise RuntimeError("TimerIO.result is not set")
        TimerIO.result.set_result(decoded)
