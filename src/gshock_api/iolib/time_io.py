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
        """
        Purely encodes a datetime into the 10-byte watch payload.
        Uses little-endian byte ordering for the year, and normal bytes for the rest.
        """
        # Byte 0-1: Year (little endian)
        year_bytes = dt.year.to_bytes(2, byteorder="little")
        
        # Bytes 2-7: Month, Day, Hour, Minute, Second, Weekday
        time_bytes = bytes([
            dt.month,
            dt.day,
            dt.hour,
            dt.minute,
            dt.second,
            dt.weekday()
        ])
        
        # Byte 8: Nanoseconds mapped to the eighth byte formula
        nanos = dt.microsecond * 1_000
        nano_byte = bytes([(nanos * 256 // 1_000_000_000) & 0xFF])
        
        # Byte 9: Constants/Flags (always 1)
        flag_byte = b"\x01"
        
        # Compose using pure Binary Monoid concatenation (+)
        return year_bytes + time_bytes + nano_byte + flag_byte


class TimeIOFunctional:
    """
    Pure functional command generator implementing Monoid B (Command Stream Monoid).
    Decoupled from networking, BLE libraries, and system clock.
    """

    @staticmethod
    def generate_request_message(current_time: float | None, offset: int) -> str:
        """
        Purely generates the JSON request message.
        """
        return json.dumps({
            "action": "SET_TIME",
            "value": {
                "time": None if current_time is None else round(current_time),
                "offset": offset,
            },
        })

    @staticmethod
    def prepare_watch_commands(message_json: str, system_time: float) -> list[BLEAction]:
        """
        Pure function to generate the BLE command stream.
        Given a request message and a deterministic system time, it returns
        an immutable list of actions to be executed.
        """
        data: dict[str, object] = json.loads(message_json)
        value: dict[str, object] = data.get("value", {})

        timestamp: float | None = value.get("time")  # type: ignore
        offset: int = int(value.get("offset", 0))      # type: ignore

        if timestamp is None:
            timestamp = system_time

        # Calculate time with offset
        date_time: datetime = datetime.fromtimestamp(timestamp + offset)
        time_payload: bytes = TimeEncoderPure.encode_current_time(date_time)
        
        # Concatenate protocol header (CURRENT_TIME = 0x09) and the payload
        packet_bytes = bytes([Protocol.CURRENT_TIME.value]) + time_payload
        
        # Return a list (Monoid B) of commands
        return [Write(handle=0x000E, data=packet_bytes)]


class TimeIO:
    """
    Stateful adapter wrapper maintaining backward compatibility.
    Acts as the interpreter for the pure commands.
    """

    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol, current_time: float | None, offset: int) -> None:
        TimeIO.connection = connection
        message_str = TimeIOFunctional.generate_request_message(current_time, offset)
        await connection.send_message(message_str)

    @staticmethod
    async def send_to_watch_set(message: str) -> None:
        # Obtain system time at invocation to pass into the pure command generator
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
                    # Ignore if the connection is closed early (lower-right button pressed)
                    logger.info(f"Ignoring {e}")


class TimeEncoder:
    """
    Legacy encoder class maintaining backward compatibility.
    Delegates to TimeEncoderPure internally.
    """

    @staticmethod
    def prepare_current_time(dt: datetime) -> bytearray:
        return bytearray(TimeEncoderPure.encode_current_time(dt))
