from __future__ import annotations

import struct

from gshock_api.cancelable_result import CancelableResult
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.utils import to_compact_string, to_hex_string


class LifelogIO:
    """Handles lifelog transfer over Data Request SP + Convoy."""

    _connection: ConnectionProtocol | None = None
    _result: CancelableResult[int] | None = None
    _buffer: bytearray = bytearray()
    _expected_len: int | None = None

    # ABL-100: steps appear at this offset in the 400-byte payload.
    _STEPS_OFFSET = 374

    @staticmethod
    async def request(connection: ConnectionProtocol, timeout: float = 60.0) -> int:
        """Start lifelog transfer and return steps."""
        LifelogIO._connection = connection
        LifelogIO._buffer = bytearray()
        LifelogIO._expected_len = None
        LifelogIO._result = CancelableResult[int](timeout=timeout)

        # DRSP start: command=0x00, category=0x11, length=0 (24-bit LE)
        start_cmd = bytes([0x00, 0x11, 0x00, 0x00, 0x00])
        await connection.write(0x11, to_compact_string(to_hex_string(start_cmd)))

        return await LifelogIO._result.get_result()

    @staticmethod
    def on_drsp_received(data: bytes) -> None:
        """Handle Data Request SP notification/indication."""
        if len(data) < 5:
            return

        command = data[0]
        category = data[1]
        if category != 0x11:
            return

        length = data[2] | (data[3] << 8) | (data[4] << 16)
        if command == 0x00:
            LifelogIO._expected_len = length

        if command == 0x04:
            # End transaction from watch
            LifelogIO._finalize_if_ready()

    @staticmethod
    def on_convoy_received(data: bytes) -> None:
        """Handle Convoy notification payload."""
        if not data:
            return

        LifelogIO._buffer.extend(data)
        if LifelogIO._expected_len is not None and len(LifelogIO._buffer) >= LifelogIO._expected_len:
            # DRSP end: command=0x04, category=0x11, length=0
            if LifelogIO._connection is not None:
                end_cmd = bytes([0x04, 0x11, 0x00, 0x00, 0x00])
                # Best effort; failures should not block parsing.
                try:
                    # fire-and-forget; connection.write is async, but we can't await here
                    # callers should rely on finalization below
                    import asyncio

                    asyncio.create_task(
                        LifelogIO._connection.write(
                            0x11, to_compact_string(to_hex_string(end_cmd))
                        )
                    )
                except Exception:
                    pass
            LifelogIO._finalize_if_ready()

    @staticmethod
    def _finalize_if_ready() -> None:
        if LifelogIO._result is None:
            return

        if LifelogIO._expected_len is None:
            return

        if len(LifelogIO._buffer) < LifelogIO._expected_len:
            return

        if len(LifelogIO._buffer) >= LifelogIO._STEPS_OFFSET + 4:
            steps = struct.unpack_from("<I", LifelogIO._buffer, LifelogIO._STEPS_OFFSET)[0]
            LifelogIO._result.set_result(steps)
