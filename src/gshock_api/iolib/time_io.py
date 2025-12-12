from datetime import datetime
import json
import time
from typing import Optional

from gshock_api.iolib.connection_protocol import ConnectionProtocol

from gshock_api.casio_constants import CasioConstants
from gshock_api.exceptions import GShockIgnorableException
from gshock_api.logger import logger
from gshock_api.utils import to_compact_string, to_hex_string
from gshock_api.iolib.packet import Header, Payload, Protocol


CHARACTERISTICS: dict[str, int] = CasioConstants.CHARACTERISTICS


class TimeIO:
    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol, current_time: Optional[float], offset: int) -> None:
        TimeIO.connection = connection
        message: dict[str, object] = {
            "action": "SET_TIME",
            "value": {
                "time": None if current_time is None else round(current_time),
                "offset": offset,  # must always be an integer
            },
        }
        await connection.send_message(json.dumps(message))

    @staticmethod
    async def send_to_watch_set(message: str) -> None:
        data: dict[str, object] = json.loads(message)
        value: dict[str, object] = data.get("value", {})


        timestamp: float | None = value.get("time")  # type: ignore
        offset: int = int(value.get("offset", 0))      # type: ignore

        if timestamp is None:
            timestamp = time.time()

        date_time_ms: int = int(timestamp + offset)

        date_time: datetime = datetime.fromtimestamp(date_time_ms)
        time_data: bytearray = TimeEncoder.prepare_current_time(date_time)
        
        # protocol=0x09 (CURRENT_TIME), payload=time_data
        payload = Payload(data=time_data)
        packet_bytes = bytearray([Protocol.CURRENT_TIME.value]) + payload.data
        
        time_command: str = to_hex_string(packet_bytes)
        
        if TimeIO.connection is None:
            raise RuntimeError("TimeIO.connection is not set")
        try:
            await TimeIO.connection.write(0xE, to_compact_string(time_command))
        except GShockIgnorableException as e:
            # Ignore this exception if LOWER-RIGHT button pressed; connection closed early.
            logger.info(f"Ignoring {e}")


class TimeEncoder:
    @staticmethod
    def prepare_current_time(dt: datetime) -> bytearray:
        arr: bytearray = bytearray(10)
        year: int = dt.year
        arr[0] = year & 0xFF
        arr[1] = (year >> 8) & 0xFF
        arr[2] = dt.month
        arr[3] = dt.day
        arr[4] = dt.hour
        arr[5] = dt.minute
        arr[6] = dt.second
        arr[7] = dt.weekday()
        arr[8] = 0
        arr[9] = 1
        return arr
