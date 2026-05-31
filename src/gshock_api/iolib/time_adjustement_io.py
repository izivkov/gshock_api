import json

from gshock_api.cancelable_result import CancelableResult
from gshock_api.iolib.actions import BLEAction, Write
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.iolib.error_io import ErrorIO
from gshock_api.iolib.packet import Protocol
from gshock_api.logger import logger
from gshock_api.utils import to_compact_string, to_hex_string, to_int_array


class TimeAdjustmentIOFunctional:
    """
    Pure functional time adjustment modules implementing Monoids.
    """

    @staticmethod
    def encode(original_hex: str, time_adjustment: bool, minutes_after_hour: int) -> bytes:
        int_array = to_int_array(original_hex)
        int_array[12] = 0x80 if not time_adjustment else 0x00
        int_array[13] = minutes_after_hour
        return bytes(int_array)

    @staticmethod
    def decode(data_bytes: bytes) -> dict[str, str]:
        time_adjusted = int(data_bytes[12]) == 0x00
        minutes_after_hour = int(data_bytes[13])
        return {
            "timeAdjusment": str(time_adjusted),
            "minutesAfterHour": str(minutes_after_hour),
        }

    @staticmethod
    def prepare_watch_commands() -> list[BLEAction]:
        return [
            Write(
                handle=0x000C,
                data=bytes([Protocol.SETTING_FOR_BLE.value])
            )
        ]

    @staticmethod
    def prepare_watch_commands_set(message_json: str, original_hex: str) -> list[BLEAction]:
        parsed_message = json.loads(message_json)
        time_adjustment: bool = parsed_message.get("timeAdjustment") == "True"
        minutes_after_hour: int = int(parsed_message.get("minutesAfterHour", "0"))

        encoded = TimeAdjustmentIOFunctional.encode(original_hex, time_adjustment, minutes_after_hour)
        return [Write(handle=0x000E, data=encoded)]


class TimeAdjustmentIO:
    """
    Stateful backward-compatible wrapper.
    Acts as the interpreter for TimeAdjustmentIOFunctional commands.
    """
    result: CancelableResult[dict[str, object]] | None = None
    connection: ConnectionProtocol | None = None
    original_value: str | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol) -> CancelableResult[dict[str, object]]:
        TimeAdjustmentIO.connection = connection
        await connection.request(f"{Protocol.SETTING_FOR_BLE.value:02X}")
        TimeAdjustmentIO.result = CancelableResult[dict[str, object]]()
        return await TimeAdjustmentIO.result.get_result()

    @staticmethod
    def send_to_watch(_message: str) -> None:
        if TimeAdjustmentIO.connection is None:
            raise RuntimeError("TimeAdjustmentIO.connection is not set")

        commands = TimeAdjustmentIOFunctional.prepare_watch_commands()
        for command in commands:
            if isinstance(command, Write):
                TimeAdjustmentIO.connection.write(command.handle, command.data)

    @staticmethod
    async def send_to_watch_set(message: str) -> dict[str, str] | None:
        if TimeAdjustmentIO.original_value is None:
            return await ErrorIO.request("Error: Must call get before set")

        if TimeAdjustmentIO.connection is None:
            raise RuntimeError("TimeAdjustmentIO.connection is not set")

        commands = TimeAdjustmentIOFunctional.prepare_watch_commands_set(
            message, TimeAdjustmentIO.original_value
        )
        for command in commands:
            if isinstance(command, Write):
                write_cmd = to_compact_string(to_hex_string(command.data))
                await TimeAdjustmentIO.connection.write(0x000E, write_cmd)
        return None

    @staticmethod
    def on_received(message: bytes) -> None:
        TimeAdjustmentIO.original_value = to_hex_string(message)  # save original message

        decoded_dict = TimeAdjustmentIOFunctional.decode(message)

        if TimeAdjustmentIO.result is None:
            raise RuntimeError("TimeAdjustmentIO.result is not set")
        TimeAdjustmentIO.result.set_result(decoded_dict)  # type: ignore[arg-type]

    @staticmethod
    async def on_received_set(message: bytes) -> None:
        logger.info(f"TimeAdjustmentIO onReceivedSet: {message}")
