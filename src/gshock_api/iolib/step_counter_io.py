from typing import Final

from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.pending_requests_registry import PendingRequestsRegistry


class StepCounterIO:
    """Reads the daily step summary record from ABL-100WE activity notifications."""

    result: CancelableResult[int] | None = None
    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol) -> int:
        StepCounterIO.connection = connection
        StepCounterIO.result = CancelableResult[int]()
        PendingRequestsRegistry.register("StepCounterIO", StepCounterIO.result)

        try:
            # Notifications for the convoy/activity characteristic are enabled
            # centrally in `Connection.connect()`. Rely on the centralized
            # router instead of re-subscribing here.
            await connection.write(
                CasioConstants.HANDLE_DATA_REQUEST_SP,
                bytes([0x00, 0x11, 0x00, 0x00, 0x00]),
            )

            return await StepCounterIO.result.get_result()
        finally:
            PendingRequestsRegistry.unregister("StepCounterIO")

    @staticmethod
    def on_received(data: bytes) -> None:
        if StepCounterIO.result is None:
            return

        step_count = StepCounterIO.parse_step_counter(data)
        if step_count is not None:
            StepCounterIO.result.set_result(step_count)

    @staticmethod
    def parse_step_counter(payload: bytes) -> int | None:
        if len(payload) < 10 or payload[0] != 0x26:
            return None

        sentinel4: Final[bytes] = b"\xfe\xff\xff\xff"

        found_indices: list[int] = [
            i for i in range(6, len(payload) - 3)
            if payload[i : i + 4] == sentinel4
        ]

        if found_indices:
            # Last 4-byte sentinel ends at tail_index.
            # Skip the 4-byte sub-record header (fe 1a 00 00) that follows
            # the sentinel block — the step uint32 is 4 bytes further in.
            tail_index = found_indices[-1] + 4  # end of last sentinel
            step_offset = tail_index + 4        # skip fe + 1a 00 00 sub-header
            if step_offset + 4 <= len(payload):
                return int.from_bytes(
                    payload[step_offset : step_offset + 4], "little"
                )

        # Fallback: scan past 2-byte feff sentinels and zeros
        cursor = 6
        while cursor + 2 <= len(payload) and payload[cursor : cursor + 2] == b"\xfe\xff":
            cursor += 2
        while cursor + 2 <= len(payload) and payload[cursor : cursor + 2] == b"\x00\x00":
            cursor += 2
        # Also skip the sub-record header byte (0xfe) and 3-byte marker
        if cursor < len(payload) and payload[cursor] == 0xfe:
            cursor += 4  # skip fe 1a 00 00
        if cursor + 4 <= len(payload):
            return int.from_bytes(payload[cursor : cursor + 4], "little")

        return None