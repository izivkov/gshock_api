"""
GW-BX5600 / GMW-BZ5000 time-set implementation.

Protocol confirmed from btsnoop_hci_bx.log:

  For each of three SP steps, the watch sends a fragmented notification on
  SP_DATA (0x0019). We reassemble fragments in on_received(), apply a simple
  transform to produce the write-back payload, then send it back.

  Step 1  request "051d..."  → 101-byte notification → change byte[0] 0x05→0x02,
                               fill bytes[27:35] with 0xFF → write 35B
  Step 2  request "031e..."  → 28-byte notification  → change byte[0] 0x03→0x06
                               → write full notification
  Step 3  request "061f..."  → 133-byte notification → write-back unchanged
  Step 4  no request         → write 11-byte time command to ALL_FEATURES (0x000E)

Handles:
  SP_REQUEST   = 0x0017  write-without-response
  SP_DATA      = 0x0019  write-with-response + notify
  ALL_FEATURES = 0x000E  write-with-response
"""

import asyncio
from datetime import datetime
from typing import ClassVar

from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.logger import logger

SP_REQUEST   = CasioConstants.HANDLE_SP_REQUEST        # 0x17 → 26eb002e
SP_DATA      = CasioConstants.HANDLE_SP_DATA           # 0x19 → 26eb002f
ALL_FEATURES = CasioConstants.HANDLE_ALL_FEATURES_WRITE  # 0x0E → 26eb002d

class GwBx5600TimeIO:
    """Sets the time on a GW-BX5600 / GMW-BZ5000 watch.

    Uses a read-modify-write approach: requests current SP data from the
    watch, reassembles the fragmented notification, applies the required
    transform, and writes back — so world city and DST data are always
    taken from the watch itself rather than hardcoded.
    """

    connection:   ClassVar[ConnectionProtocol | None] = None
    result:       ClassVar[CancelableResult[bytes] | None] = None
    _step:        ClassVar[int] = 0
    _accumulator: ClassVar[bytes] = b""

    # ── Public entry point ────────────────────────────────────────────────────

    @staticmethod
    async def set_time(
        connection: ConnectionProtocol, now: datetime | None = None
    ) -> None:
        """Read current SP data from watch, modify, write back, then set time."""
        if now is None:
            now = datetime.now()
        logger.info(f"GwBx5600TimeIO.set_time: {now}")

        from gshock_api.watch_info import watch_info
        import math

        GwBx5600TimeIO.connection = connection

        # Step 1 ──────────────────────────────────────────────────────────────
        logger.info("Step 1/4: time-slot data")
        
        req1 = bytearray([0x05])
        req1.extend([0x1D, 0x00, 0x1D, 0x00]) # DST Watch State blocks
        req1.extend([0x24, 0x00, 0x24, 0x01, 0x24, 0x02]) # Time Slot blocks
        
        notif1 = await GwBx5600TimeIO._request(connection, 1, req1.hex())
        
        # The write-back for step 1 only expects a subset of the full 101B payload.
        # We slice exactly what is needed and convert it into a write command (0x02).
        wb1_length = 35 
        wb1 = bytearray(notif1[:wb1_length])
        wb1[0] = 0x02                   # command byte: read (0x05) → write (0x02)
        
        # Fill trailing bytes with 0xFF as expected by the watch
        for i in range(27, min(wb1_length, len(wb1))):
            wb1[i] = 0xFF
            
        await connection.write(SP_DATA, bytes(wb1))

        # Step 2 ──────────────────────────────────────────────────────────────
        logger.info("Step 2/4: world-city data")
        
        # 0x03 is the bulk read command for DST setting
        req2 = bytearray([0x03])
        # The watch groups DST data; each 1E00 block returns data for 2 cities.
        blocks = math.ceil(watch_info.worldCitiesCount / 2)
        for _ in range(blocks):
            req2.extend([CasioConstants.CHARACTERISTICS["CASIO_DST_SETTING"], 0x00])
            
        notif2 = await GwBx5600TimeIO._request(connection, 2, req2.hex())
        
        wb2 = bytearray(notif2)
        wb2[0] = 0x06                   # command byte: read (0x03) → write (0x06)
        await connection.write(SP_DATA, bytes(wb2))

        # Step 3 ──────────────────────────────────────────────────────────────
        logger.info("Step 3/4: city names")
        
        # 0x06 is the bulk read command for World Cities
        req3 = bytearray([0x06])
        for i in range(watch_info.worldCitiesCount):
            # Casio interleaves city indices in the bulk request (e.g. 0, 6, 1, 7, 2, 8)
            idx = (i // 2) + (6 if i % 2 != 0 else 0)
            req3.extend([CasioConstants.CHARACTERISTICS["CASIO_WORLD_CITIES"], idx])
            
        notif3 = await GwBx5600TimeIO._request(connection, 3, req3.hex())
        
        # Write-back is identical to notification — no transform needed
        await connection.write(SP_DATA, bytes(notif3))

        # Step 4 ──────────────────────────────────────────────────────────────
        await GwBx5600TimeIO._write_time_command(connection, now)
        logger.info("GwBx5600TimeIO.set_time: complete")

    # ── Public entry point (matches IO class convention) ──────────────────────

    @staticmethod
    async def request(
        connection: ConnectionProtocol, current_time: float | None = None, offset: int = 0
    ) -> None:
        """Conforms to the IO class convention used by TimeIO, AlarmsIO, etc.

        Called from GshockAPI.set_time() via message_dispatcher.GwBx5600TimeIO.request().
        Delegates directly to set_time().
        """
        import time
        if current_time is None:
            current_time = time.time()
            
        now = datetime.fromtimestamp(current_time + offset)
        await GwBx5600TimeIO.set_time(connection, now)

    # ── Dispatcher entry point ────────────────────────────────────────────────

    @staticmethod
    def on_received(data: bytes) -> None:
        """Accumulate fragmented SP_DATA notifications and deliver when complete.

        The watch sends SP_DATA notifications fragmented across multiple BLE
        packets (MTU ~20B). The message_dispatcher calls on_received() once
        per fragment. We accumulate until we reach the expected size for the
        current step, then set the CancelableResult.
        """
        from gshock_api.watch_info import watch_info
        import math

        if GwBx5600TimeIO.result is None:
            return

        GwBx5600TimeIO._accumulator += data

        if GwBx5600TimeIO._step == 1:
            # Step 1: 1 byte header + 2 blocks of 1D (DST state) + 3 blocks of 24 (Time slot)
            # Size on BX is 101 bytes. 
            expected = 101
        elif GwBx5600TimeIO._step == 2:
            # Step 2: 1 byte header + (blocks * 9 bytes each)
            blocks = math.ceil(watch_info.worldCitiesCount / 2)
            expected = 1 + (blocks * 9)
        elif GwBx5600TimeIO._step == 3:
            # Step 3: 1 byte header + (cities * 22 bytes each)
            expected = 1 + (watch_info.worldCitiesCount * 22)
        else:
            expected = 0

        accumulated = len(GwBx5600TimeIO._accumulator)

        logger.debug(
            f"GwBx5600TimeIO.on_received: step={GwBx5600TimeIO._step} "
            f"accumulated={accumulated}B / expected={expected}B"
        )

        if accumulated >= expected:
            GwBx5600TimeIO.result.set_result(GwBx5600TimeIO._accumulator)

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    async def _request(
        connection: ConnectionProtocol, step: int, req_payload: str
    ) -> bytes:
        """Send an SP request and wait for the fully reassembled notification."""
        GwBx5600TimeIO._step = step
        GwBx5600TimeIO._accumulator = b""
        GwBx5600TimeIO.result = CancelableResult[bytes]()
        try:
            await connection.write(SP_REQUEST, req_payload)
            return await asyncio.wait_for(
                GwBx5600TimeIO.result.get_result(), timeout=5.0
            )
        finally:
            GwBx5600TimeIO.result = None
            GwBx5600TimeIO._accumulator = b""
            GwBx5600TimeIO._step = 0

    @staticmethod
    async def _write_time_command(
        connection: ConnectionProtocol, now: datetime
    ) -> None:
        """Write the 11-byte time command to ALL_FEATURES (0x000E).

        Format confirmed from snoop log [1251]:
          09 {year_lo} {year_hi} {month} {day} {hour} {min} {sec} {dow} 50 01
          Casio DOW: Sun=0, Mon=1 … Sat=6
          0x50 = DST/timezone flags constant from log
        """
        casio_dow = (now.weekday() + 1) % 7

        time_cmd = bytes([
            0x09,
            now.year & 0xFF,
            (now.year >> 8) & 0xFF,
            now.month,
            now.day,
            now.hour,
            now.minute,
            now.second,
            casio_dow,
            0x50,
            0x01,
        ])
        logger.info(f"Step 4/4: time command: {time_cmd.hex()}")
        await connection.write(ALL_FEATURES, time_cmd.hex())
