import asyncio
import contextlib
from typing import Final

from gshock_api.cancelable_result import CancelableResult
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.logger import logger

class StepCounterIO:
    """Reads the daily step total from the ABL-100WE life-log notification.

    Protocol (confirmed from HCI snoop log):
      1. Send request bytes [00 11 00 00 00] to handle 0x0011
         (CASIO_DATA_REQUEST_SP).
      2. Watch acknowledges on handle 0x0011.
      3. Watch sends a 398-byte life-log notification on handle 0x0014
         (CASIO_CONVOY), fragmented across ~15 L2CAP packets.
      4. on_received() parses the notification and sets the result.

    Payload structure of the 0x0014 notification:
      [0]      0x26  record type (life-log)
      [1]      day of week (1=Mon … 7=Sun)
      [2]      month
      [3]      0x18 = 24 hourly slot count
      [4:6]    flags
      [6..]    hourly slots: 0xFEFF = empty, or actual per-hour count
      [tail]   4-byte sub-record header (skip entirely)
      [tail+4] uint32 LE daily step total
    """
    STEPS_OFFSET: Final[int] = 374
    RECORD_TYPE_LIFELOG: Final[int] = 0x26

    result: CancelableResult[int] | None = None
    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol) -> int:
        StepCounterIO.connection = connection
        StepCounterIO.result = CancelableResult[int]()
        await connection.write(
            0x0011,
            bytes([0x00, 0x11, 0x00, 0x00, 0x00]),
        )
        return await StepCounterIO.result.get_result()

    @staticmethod
    def on_received(data: bytes) -> None:
        if StepCounterIO.result is None:
            return

        # The watch expects the transaction to be closed even if we fail to
        # parse; leaving it open makes every subsequent request time out.
        StepCounterIO._end_transaction()

        step_count = StepCounterIO.parse_step_counter(data)
        if step_count is None:
            logger.warning(
                f"Could not parse step count from {len(data)}-byte life-log "
                f"payload (expected 400). Head: {data[:16].hex()}"
            )
            return
        StepCounterIO.result.set_result(step_count)

    @staticmethod
    def _end_transaction() -> None:
        """Send the DRSP end command [04 11 00 00 00], as the official app does."""
        connection = StepCounterIO.connection
        if connection is None:
            return
        with contextlib.suppress(RuntimeError):
            asyncio.get_running_loop()
            asyncio.create_task(  # noqa: RUF006
                connection.write(0x0011, bytes([0x04, 0x11, 0x00, 0x00, 0x00]))
            )

    @staticmethod
    def parse_step_counter(payload: bytes) -> int | None:
        """Extract the daily step total from an ABL-100WE life-log payload.

        Returns None rather than guessing if the record is truncated or is
        not a life-log record — a wrong number is worse than no number.
        """
        offset = StepCounterIO.STEPS_OFFSET
        # Check if the first byte is 0x26
        if payload[:1] != bytes([StepCounterIO.RECORD_TYPE_LIFELOG]):
            return None
        if len(payload) < offset + 4:
            return None

        return int.from_bytes(payload[offset : offset + 4], "little")

    