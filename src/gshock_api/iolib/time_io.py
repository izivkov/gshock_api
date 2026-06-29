"""
time_io.py — Time (0x09) characteristic I/O.
"""

from datetime import datetime
import json
import time

from gshock_api.exceptions import GShockIgnorableException
from gshock_api.iolib.actions import BLEAction, Write
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.iolib.packet import Protocol
from gshock_api.logger import logger
from gshock_api.utils import to_compact_string, to_hex_string


class TimeEncoderPure:
    """
    Pure functional current time encoder implementing Monoid A (Binary Monoid).
    Contains no mutable state, side effects, or I/O.
    """

    @staticmethod
    def encode_current_time(dt: datetime) -> bytes:
        year_bytes = dt.year.to_bytes(2, byteorder="little")
        time_bytes = bytes([
            dt.month,
            dt.day,
            dt.hour,
            dt.minute,
            dt.second,
            dt.weekday()
        ])
        nanos = dt.microsecond * 1_000
        nano_byte = bytes([(nanos * 256 // 1_000_000_000) & 0xFF])
        flag_byte = b"\x01"
        return year_bytes + time_bytes + nano_byte + flag_byte


class TimeIOFunctional:
    """
    Pure functional command generator implementing Monoid B (Command Stream Monoid).
    Decoupled from networking, BLE libraries, and system clock.
    """

    @staticmethod
    def generate_request_message(current_time: float | None, offset: int) -> str:
        return json.dumps({
            "action": "SET_TIME",
            "value": {
                "time": None if current_time is None else round(current_time),
                "offset": offset,
            },
        })

    @staticmethod
    def prepare_watch_commands(message_json: str, system_time: float) -> list[BLEAction]:
        data: dict = json.loads(message_json)
        value: dict = data.get("value", {})

        timestamp: float | None = value.get("time")
        offset: int = int(value.get("offset", 0))

        if timestamp is None:
            timestamp = system_time

        date_time = datetime.fromtimestamp(timestamp + offset)
        time_payload = TimeEncoderPure.encode_current_time(date_time)
        packet_bytes = bytes([Protocol.CURRENT_TIME.value]) + time_payload

        return [Write(handle=0x000E, data=packet_bytes)]


class TimeIO:
    """
    Stateful adapter wrapper maintaining backward compatibility.
    Acts as the interpreter for the pure commands.
    Initialization of DST and world cities is handled upstream in GshockAPI.
    """

    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(
        connection: ConnectionProtocol,
        current_time: float | None,
        offset: int,
    ) -> None:
        TimeIO.connection = connection
        message_str = TimeIOFunctional.generate_request_message(current_time, offset)
        await connection.send_message(message_str)

    @staticmethod
    async def send_to_watch_set(message: str) -> None:
        system_time = time.time()
        commands = TimeIOFunctional.prepare_watch_commands(message, system_time)

        if TimeIO.connection is None:
            raise RuntimeError("TimeIO.connection is not set")

        for command in commands:
            if isinstance(command, Write):
                time_command: str = to_hex_string(command.data)
                try:
                    await TimeIO.connection.write(
                        command.handle,
                        to_compact_string(time_command)
                    )
                except GShockIgnorableException as e:
                    logger.info(f"Ignoring {e}")


class TimeEncoder:
    """
    Legacy encoder class maintaining backward compatibility.
    Delegates to TimeEncoderPure internally.
    """

    @staticmethod
    def prepare_current_time(dt: datetime) -> bytearray:
        return bytearray(TimeEncoderPure.encode_current_time(dt))
    