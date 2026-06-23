"""
GW-BX5600 / GMW-BZ5000 time-set implementation.

Two approaches available — switch by changing the call in gshock_api.py:

  await GwBx5600TimeIO.set_time_hardcoded(connection, now)   # reliable, from snoop log
  await GwBx5600TimeIO.set_time_dynamic(connection, now)     # reads from watch first (may fail on fragmentation)
"""

import asyncio
from datetime import datetime
from typing import ClassVar

from gshock_api.cancelable_result import CancelableResult
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.logger import logger
from gshock_api.pending_requests_registry import PendingRequestsRegistry

SP_REQUEST = 0x0017
SP_DATA    = 0x0019


class GwBx5600TimeIO:
    connection: ClassVar[ConnectionProtocol | None] = None
    result: ClassVar[CancelableResult[bytes] | None] = None

    # ── Request / on_received (used by set_time_dynamic) ─────────────────────

    @staticmethod
    async def request(
        connection: ConnectionProtocol, step: int, req_payload: str
    ) -> bytes:
        GwBx5600TimeIO.connection = connection
        request_name = f"GwBx5600TimeIO_{step}"
        GwBx5600TimeIO.result = CancelableResult[bytes]()
        PendingRequestsRegistry.register(request_name, GwBx5600TimeIO.result)
        try:
            await connection.write(SP_REQUEST, req_payload)
            return await asyncio.wait_for(
                GwBx5600TimeIO.result.get_result(), timeout=5.0
            )
        finally:
            PendingRequestsRegistry.unregister(request_name)
            GwBx5600TimeIO.result = None

    @staticmethod
    def on_received(data: bytes) -> None:
        if GwBx5600TimeIO.result is not None:
            GwBx5600TimeIO.result.set_result(data)

    # ── Hardcoded set_time (reliable — values from btsnoop_hci_bx.log) ───────

    @staticmethod
    async def set_time_hardcoded(
        connection: ConnectionProtocol, now: datetime | None = None
    ) -> None:
        """
        Set time using hardcoded SP payloads verified byte-for-byte against
        btsnoop_hci_bx.log (GMW-BZ5000 / GW-BX5600 capture).

        Does NOT wait for any notifications from the watch — just replays
        the known-good request/write-back pairs, then sends the current time.

        Use this until set_time_dynamic() fragmentation is resolved.
        """
        if now is None:
            now = datetime.now()

        logger.info(f"GwBx5600TimeIO.set_time_hardcoded: setting time to {now}")

        # Step 1: time slot data
        logger.info("Step 1/4: time slot data (hardcoded)")
        await connection.write(SP_REQUEST, "051d001d00240024012402")
        await asyncio.sleep(0.15)
        await connection.write(
            SP_DATA,
            "020f001d00010606e9760000ffffffffffff0f001d020302001901ffffffffffffffff"
        )
        await asyncio.sleep(0.15)

        # Step 2: world city data
        logger.info("Step 2/4: world city data (hardcoded)")
        await connection.write(SP_REQUEST, "031e001e001e00")
        await asyncio.sleep(0.15)
        await connection.write(
            SP_DATA,
            "0607001e00e97604040207001e01000000000007001e02190124040014002400"
            "014044ba36ef8055fc4002007372be637d041400240101000000000000000000"
            "000000000000000014002402010000000000000000000000000000000002"
        )
        await asyncio.sleep(0.15)

        # Step 3: city names
        logger.info("Step 3/4: city names (hardcoded)")
        await connection.write(SP_REQUEST, "061f001f061f011f071f021f08")
        await asyncio.sleep(0.15)
        await connection.write(
            SP_DATA,
            "0614001f004d414452494400000000000000000000000014001f064d41440000"
            "0000000000000000000000000014001f0128555443290000000000000000000"
            "000000014001f0755544300000000000000000000000000000000000014001f"
            "02544f4b594f0000000000000000000000000014001f0854594f000000000000"
            "00000000000000000000"
        )
        await asyncio.sleep(0.15)

        # Step 4: final time command on ALL_FEATURES (0x000E)
        await GwBx5600TimeIO._write_time_command(connection, now)
        logger.info("GwBx5600TimeIO.set_time_hardcoded: complete")

    # ── Dynamic set_time (reads from watch — may fail on fragmentation) ───────

    @staticmethod
    async def set_time_dynamic(
        connection: ConnectionProtocol, now: datetime | None = None
    ) -> None:
        """
        Set time using read-modify-write: reads current SP data from the watch,
        modifies command byte, writes back, then sends the current time.

        NOTE: Currently unreliable because the watch's 0x0019 notifications are
        MTU-fragmented (~20 bytes per packet) but we only capture the first
        fragment. Steps 2 and 3 will be truncated. Use set_time_hardcoded()
        until this is fixed.
        """
        from gshock_api.exceptions import GShockError

        if now is None:
            now = datetime.now()

        logger.info(f"GwBx5600TimeIO.set_time_dynamic: setting time to {now}")

        # Step 1: time slot data
        try:
            notif1 = await GwBx5600TimeIO.request(
                connection, 1, "051d001d00240024012402"
            )
            logger.debug(f"Step 1 notification ({len(notif1)}B): {notif1.hex()}")
            resp1 = bytearray(notif1[:35])
            if resp1:
                resp1[0] = 0x02
            if len(resp1) >= 35:
                for i in range(27, 35):
                    resp1[i] = 0xFF
            else:
                logger.warning(
                    f"Step 1 too short ({len(resp1)}B), skipping byte 27-34 fill"
                )
            await connection.write(SP_DATA, resp1.hex())
        except asyncio.TimeoutError:
            raise GShockError("Step 1 timeout — watch did not respond on 0x0019")
        await asyncio.sleep(0.15)

        # Step 2: world city data
        try:
            notif2 = await GwBx5600TimeIO.request(
                connection, 2, "031e001e001e00"
            )
            logger.debug(f"Step 2 notification ({len(notif2)}B): {notif2.hex()}")
            if len(notif2) < 90:
                logger.warning(
                    f"Step 2 may be fragmented ({len(notif2)}B, expected ~90)"
                )
            resp2 = bytearray(notif2)
            if resp2:
                resp2[0] = 0x06
            await connection.write(SP_DATA, resp2.hex())
        except asyncio.TimeoutError:
            raise GShockError("Step 2 timeout — watch did not respond on 0x0019")
        await asyncio.sleep(0.15)

        # Step 3: city names
        try:
            notif3 = await GwBx5600TimeIO.request(
                connection, 3, "061f001f061f011f071f021f08"
            )
            logger.debug(f"Step 3 notification ({len(notif3)}B): {notif3.hex()}")
            if len(notif3) < 120:
                logger.warning(
                    f"Step 3 may be fragmented ({len(notif3)}B, expected ~120)"
                )
            resp3 = bytearray(notif3)
            if resp3:
                resp3[0] = 0x06
            await connection.write(SP_DATA, resp3.hex())
        except asyncio.TimeoutError:
            raise GShockError("Step 3 timeout — watch did not respond on 0x0019")
        await asyncio.sleep(0.5)

        # Step 4: final time command
        await GwBx5600TimeIO._write_time_command(connection, now)
        logger.info("GwBx5600TimeIO.set_time_dynamic: complete")

    # ── Shared: final time command ────────────────────────────────────────────

    @staticmethod
    async def _write_time_command(
        connection: ConnectionProtocol, now: datetime
    ) -> None:
        """
        Writes the final 11-byte time command to ALL_FEATURES (0x000E).
        Format confirmed from two independent snoop logs:
          09 {year_lo} {year_hi} {month} {day} {hour} {min} {sec} {dow} {dst} 01
        Casio day-of-week: Sun=0, Mon=1 ... Sat=6
        """
        casio_dow = (now.weekday() + 1) % 7  # Python Mon=0 → Casio Mon=1, Sun=0

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
            0x50,   # DST/timezone flags from snoop log
            0x01,
        ])
        logger.info(f"Step 4/4: time command: {time_cmd.hex()}")
        await connection.write(0x000E, time_cmd.hex())
        