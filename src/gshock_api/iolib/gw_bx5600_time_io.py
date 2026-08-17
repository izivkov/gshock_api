"""
GW-BX5600 / GMW-BZ5000 time-set implementation.

Protocol confirmed from btsnoop_hci_bx.log and matching GShockAPI Kotlin:

  For each of three SP steps, the watch sends a fragmented notification on
  SP_DATA (0x0019). We reassemble fragments in on_received(), apply a simple
  transform to produce the write-back payload, then send it back.

  Step 1  request "051d..."  → 101-byte notification → change byte[0] 0x05→0x02 → write 101B
  Step 2  request "031e..."  → 28-byte notification  → change byte[0] 0x03→0x06 + append 66B city records → write 94B
  Step 3  request "061f..."  → 133-byte notification → write-back unchanged
  Step 4  no request         → write 11-byte time command to ALL_FEATURES (0x000E)

Handles:
  SP_REQUEST   = 0x0017  write-without-response
  SP_DATA      = 0x0019  write-with-response + notify
  ALL_FEATURES = 0x000E  write-with-response
"""

import asyncio
from datetime import datetime
import math
import struct
from typing import ClassVar

from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.casio_time_zone_helper import CasioTimeZoneHelper
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.logger import logger

SP_REQUEST = CasioConstants.HANDLE_SP_REQUEST
SP_DATA = CasioConstants.HANDLE_SP_DATA
ALL_FEATURES = CasioConstants.HANDLE_ALL_FEATURES_WRITE

CITY_RECORD_FLAG = 0x01
EMPTY_SLOT_TRAILING = 0x00
EMPTY_SLOT_LAT = 0.0
EMPTY_SLOT_LON = 0.0


class GwBx5600TimeIO:
    """Sets the time on a GW-BX5600 / GMW-BZ5000 watch."""

    connection: ClassVar[ConnectionProtocol | None] = None
    result: ClassVar[CancelableResult[bytes] | None] = None
    _step: ClassVar[int] = 0
    _accumulator: ClassVar[bytes] = b""

    @staticmethod
    async def set_time(
        connection: ConnectionProtocol, now: datetime | None = None
    ) -> None:
        """Read current SP data from watch, modify, write back, then set time."""
        from gshock_api.watch_info import watch_info

        if now is None:
            now = datetime.now()
        logger.info(f"GwBx5600TimeIO.set_time: {now}")

        GwBx5600TimeIO.connection = connection

        # Step 1 ──────────────────────────────────────────────────────────────
        logger.info("Step 1/4: time-slot data")
        req1 = bytearray([0x05])
        req1.extend([0x1D, 0x00, 0x1D, 0x00])  # DST Watch State blocks
        req1.extend([0x24, 0x00, 0x24, 0x01, 0x24, 0x02])  # Time Slot blocks

        notif1 = await GwBx5600TimeIO._request(connection, 1, req1.hex())

        wb1 = bytearray(notif1)
        wb1[0] = 0x02  # command byte: read (0x05) → write (0x02)
        logger.debug(f"GwBx5600TimeIO Step1 write: {len(wb1)}B")
        await connection.write(SP_DATA, bytes(wb1))

        # Step 2 ──────────────────────────────────────────────────────────────
        logger.info("Step 2/4: world-city data")
        req2 = bytearray([0x03])
        blocks = math.ceil(watch_info.worldCitiesCount / 2)
        for _ in range(blocks):
            req2.extend([CasioConstants.CHARACTERISTICS["CASIO_DST_SETTING"], 0x00])

        notif2 = await GwBx5600TimeIO._request(connection, 2, req2.hex())

        wb2 = bytearray(notif2)
        wb2[0] = 0x06  # command byte: read (0x03) → write (0x06)
        with_city_data = bytes(wb2) + GwBx5600TimeIO._build_world_city_records()
        logger.debug(f"GwBx5600TimeIO Step2 write: {len(with_city_data)}B (expect 94)")
        await connection.write(SP_DATA, with_city_data)

        # Step 3 ──────────────────────────────────────────────────────────────
        logger.info("Step 3/4: city names")
        req3 = bytearray([0x06])
        for i in range(watch_info.worldCitiesCount):
            idx = (i // 2) + (6 if i % 2 != 0 else 0)
            req3.extend([CasioConstants.CHARACTERISTICS["CASIO_WORLD_CITIES"], idx])

        notif3 = await GwBx5600TimeIO._request(connection, 3, req3.hex())
        logger.debug(f"GwBx5600TimeIO Step3 write: {len(notif3)}B")
        await connection.write(SP_DATA, bytes(notif3))

        # Step 4 ──────────────────────────────────────────────────────────────
        await GwBx5600TimeIO._write_time_command(connection, now)
        logger.info("GwBx5600TimeIO.set_time: complete")

    @staticmethod
    def _build_world_city_records() -> bytes:
        """Constructs three 22-byte city location records for Step 2."""
        casio_tz = CasioTimeZoneHelper.get_local_casio_time_zone()
        lat, lon, _ = CasioTimeZoneHelper.get_world_city_coordinates(casio_tz.zone_name)
        dst_value = 1 if casio_tz.is_in_dst() else 0

        home_record = GwBx5600TimeIO._city_record(0, lat, lon, dst_value)
        empty_slot1 = GwBx5600TimeIO._city_record(1, EMPTY_SLOT_LAT, EMPTY_SLOT_LON, EMPTY_SLOT_TRAILING)
        empty_slot2 = GwBx5600TimeIO._city_record(2, EMPTY_SLOT_LAT, EMPTY_SLOT_LON, EMPTY_SLOT_TRAILING)

        return home_record + empty_slot1 + empty_slot2

    @staticmethod
    def _city_record(slot_index: int, lat: float, lon: float, trailing: int) -> bytes:
        """Encodes a single 22-byte city location record (Big-Endian double lat/lon)."""
        return struct.pack(">BBBBBddB", 0x14, 0x00, 0x24, slot_index, CITY_RECORD_FLAG, lat, lon, trailing)

    @staticmethod
    async def request(
        connection: ConnectionProtocol, current_time: float | None = None, offset: int = 0
    ) -> None:
        import time

        if current_time is None:
            current_time = time.time()
        now = datetime.fromtimestamp(current_time + offset)
        await GwBx5600TimeIO.set_time(connection, now)

    @staticmethod
    def on_received(data: bytes) -> None:
        from gshock_api.watch_info import watch_info

        if GwBx5600TimeIO.result is None:
            return

        GwBx5600TimeIO._accumulator += data

        if GwBx5600TimeIO._step == 1:
            expected = 101
        elif GwBx5600TimeIO._step == 2:
            expected = 28
        elif GwBx5600TimeIO._step == 3:
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

    @staticmethod
    async def _request(
        connection: ConnectionProtocol, step: int, req_payload: str
    ) -> bytes:
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
        casio_dow = 7 if now.weekday() == 6 else now.weekday() + 1
        sub_second = int((now.microsecond * 256) / 1_000_000)

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
            sub_second,
            0x01,
        ])
        logger.info(f"Step 4/4: time command: {time_cmd.hex()}")
        await connection.write(ALL_FEATURES, time_cmd.hex())
