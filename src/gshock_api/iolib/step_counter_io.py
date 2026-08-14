from typing import Final

from gshock_api.cancelable_result import CancelableResult
from gshock_api.iolib.connection_protocol import ConnectionProtocol


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
        step_count = StepCounterIO.parse_step_counter(data)
        if step_count is not None:
            StepCounterIO.result.set_result(step_count)

    @staticmethod
    def parse_step_counter(payload: bytes) -> int | None:
        """Extract the daily step total from an ABL-100WE life-log payload.

        Confirmed from HCI log: 398-byte payload, daily step total = 2485
        located at byte offset 378 (last 4-byte sentinel ends at 374,
        4-byte sub-record header follows, step uint32 at 378).
        """
        if len(payload) < 10 or payload[0] != 0x26:
            return None

        # Locate the last 4-byte sentinel and skip the sub-record header
        # (4 bytes) that immediately follows — the step uint32 is next.
        sentinel4: Final[bytes] = b"\xfe\xff\xff\xff"
        found_indices: list[int] = [
            i for i in range(6, len(payload) - 3)
            if payload[i : i + 4] == sentinel4
        ]

        if found_indices:
            tail_index = found_indices[-1] + 4  # byte after last sentinel
            step_offset = tail_index + 4        # skip 4-byte sub-record header
            if step_offset + 4 <= len(payload):
                return int.from_bytes(
                    payload[step_offset : step_offset + 4], "little"
                )

        # Fallback: scan past 2-byte feff pairs and zero padding,
        # skip sub-record header, then read the uint32.
        cursor = 6
        while cursor + 2 <= len(payload) and payload[cursor : cursor + 2] == b"\xfe\xff":
            cursor += 2
        while cursor + 2 <= len(payload) and payload[cursor : cursor + 2] == b"\x00\x00":
            cursor += 2
        cursor += 4  # skip sub-record header
        if cursor + 4 <= len(payload):
            return int.from_bytes(payload[cursor : cursor + 4], "little")

        return None
    