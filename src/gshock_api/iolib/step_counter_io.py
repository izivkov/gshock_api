import struct
from typing import Final

from gshock_api.cancelable_result import CancelableResult
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.logger import logger
from gshock_api.model.step_counter_data import StepCounterData

FALLBACK_EXPECTED_LENGTH: Final[int] = 400
DRSP_CATEGORY_EXERCISE: Final[int] = 0x11
START_TRANSACTION_CMD: Final[bytes] = bytes([0x00, DRSP_CATEGORY_EXERCISE, 0x00, 0x00, 0x00])
END_TRANSACTION_CMD: Final[bytes] = bytes([0x04, DRSP_CATEGORY_EXERCISE, 0x00, 0x00, 0x00])


def _decode_bcd(byte: int) -> int:
    high, low = divmod(byte, 16)
    if high > 9 or low > 9:
        raise ValueError(f"invalid BCD byte 0x{byte:02x}")
    return high * 10 + low


class StepCounterIOFunctional:
    """Pure functional core for decoding ABL-100WE step counter (life-log) records."""

    HEADER_SIZE: Final[int] = 6
    HOURLY_SLOT_COUNT: Final[int] = 144
    HOURLY_SLOT_SIZE: Final[int] = 2
    BETWEEN_HISTORY_PADDING_SIZE: Final[int] = 24
    DAILY_SLOT_COUNT: Final[int] = 14
    DAILY_SLOT_SIZE: Final[int] = 4
    CURRENT_DISTANCE_OFFSET: Final[int] = 378
    PENDING_DISTANCE_OFFSET: Final[int] = 392
    BCD_TOTAL_OFFSET: Final[int] = 396

    @staticmethod
    def parse(payload: bytes) -> StepCounterData | None:
        if not payload or payload[0] != 0x26:
            return None

        warnings: list[str] = []

        # Decode a 6-byte BCD timestamp from payload[1:7] (year, month, day, hour, minute, second).
        timestamp = None
        try:
            if len(payload) >= 7:
                raw_ts = payload[1:7]
                vals: list[int | None] = []
                for b in raw_ts:
                    if b in (0xFE, 0xFF):
                        vals.append(None)
                    else:
                        vals.append(_decode_bcd(b))

                # Require year/month/day to construct a meaningful timestamp.
                if vals[0] is None or vals[1] is None or vals[2] is None:
                    warnings.append("incomplete BCD date in step counter header; timestamp unavailable")
                    timestamp = None
                else:
                    year = 2000 + vals[0]
                    month = vals[1]
                    day = vals[2]
                    hour = vals[3] or 0
                    minute = vals[4] or 0
                    second = vals[5] or 0
                    from datetime import datetime as _dt

                    timestamp = _dt(year, month, day, hour, minute, second)
            else:
                warnings.append("step record too short to contain timestamp")
                timestamp = None
        except ValueError:
            warnings.append("invalid BCD timestamp in step counter header; watch may have partial/fresh life-log data")
            timestamp = None

        daily_history_offset = (
            StepCounterIOFunctional.HEADER_SIZE
            + StepCounterIOFunctional.HOURLY_SLOT_COUNT * StepCounterIOFunctional.HOURLY_SLOT_SIZE
            + StepCounterIOFunctional.BETWEEN_HISTORY_PADDING_SIZE
        )
        current_day_offset = (
            daily_history_offset
            + StepCounterIOFunctional.DAILY_SLOT_COUNT * StepCounterIOFunctional.DAILY_SLOT_SIZE
        )

        hourly_steps: list[int | None] = []
        for i in range(StepCounterIOFunctional.HOURLY_SLOT_COUNT):
            offset = StepCounterIOFunctional.HEADER_SIZE + i * StepCounterIOFunctional.HOURLY_SLOT_SIZE
            if offset + StepCounterIOFunctional.HOURLY_SLOT_SIZE > len(payload):
                hourly_steps.append(None)
                continue
            val = struct.unpack_from("<H", payload, offset)[0]
            hourly_steps.append(None if val == 0xFFFE else val)

        daily_history: list[int | None] = []
        for i in range(StepCounterIOFunctional.DAILY_SLOT_COUNT):
            offset = daily_history_offset + i * StepCounterIOFunctional.DAILY_SLOT_SIZE
            if offset + StepCounterIOFunctional.DAILY_SLOT_SIZE > len(payload):
                daily_history.append(None)
                continue
            val = struct.unpack_from("<I", payload, offset)[0]
            daily_history.append(None if val == 0xFFFFFFFE else val)

        current_day_steps: int | None = None
        if current_day_offset + StepCounterIOFunctional.DAILY_SLOT_SIZE <= len(payload):
            cur_val = struct.unpack_from("<I", payload, current_day_offset)[0]
            current_day_steps = None if cur_val == 0xFFFFFFFE else cur_val

        distance_meters = None
        pending_distance_meters = None
        total_distance_meters = None
        bcd_total_steps = None

        if len(payload) < current_day_offset + StepCounterIOFunctional.DAILY_SLOT_SIZE:
            warnings.append("step record truncated; missing trailing history fields")

        if len(payload) >= StepCounterIOFunctional.CURRENT_DISTANCE_OFFSET + 4:
            distance_meters = struct.unpack_from("<I", payload, StepCounterIOFunctional.CURRENT_DISTANCE_OFFSET)[0]
            total_distance_meters = distance_meters

        if len(payload) >= StepCounterIOFunctional.PENDING_DISTANCE_OFFSET + 4:
            pending_distance_meters = struct.unpack_from("<I", payload, StepCounterIOFunctional.PENDING_DISTANCE_OFFSET)[0]

        if len(payload) >= StepCounterIOFunctional.BCD_TOTAL_OFFSET + 4:
            raw_bcd_total = payload[StepCounterIOFunctional.BCD_TOTAL_OFFSET:StepCounterIOFunctional.BCD_TOTAL_OFFSET + 4]
            if any(raw_bcd_total):
                try:
                    bcd_total_steps = 0
                    for i, byte in enumerate(raw_bcd_total):
                        bcd_total_steps += _decode_bcd(byte) * (100 ** i)
                except ValueError:
                    bcd_total_steps = None

        if (
            bcd_total_steps is not None
            and bcd_total_steps > 0
            and current_day_steps is not None
            and bcd_total_steps != current_day_steps
        ):
            warnings.append(f"BCD total {bcd_total_steps} differs from current step count {current_day_steps}")
        # Build friendly representations for callers
        # 144 slots -> 10-minute intervals
        hourly_intervals: list[dict] = []
        for i, steps in enumerate(hourly_steps):
            start = i * 10
            end = start + 9
            hourly_intervals.append({"index": i, "start_minute": start, "end_minute": end, "steps": steps})

        # Aggregate into 24 hourly totals.
        # If any 10-minute slot for an hour is missing (`None`), report the
        # whole hour as `None` to reflect incomplete data.
        hourly_by_hour: list[int | None] = []
        for h in range(24):
            slots = hourly_steps[h * 6 : h * 6 + 6]
            if any(s is None for s in slots):
                hourly_by_hour.append(None)
            else:
                total = sum(s for s in slots)  # all slots are ints
                hourly_by_hour.append(total)

        # Daily history as list of dicts: days_ago=1 is most recent previous day
        daily_history_list = [{"days_ago": i + 1, "steps": v} for i, v in enumerate(daily_history)]

        return StepCounterData(
            timestamp=timestamp,
            hourly_steps=hourly_steps,
            daily_history=daily_history,
            current_day_steps=current_day_steps,
            raw=payload,
            warnings=warnings,
            distance_meters=distance_meters,
            pending_distance_meters=pending_distance_meters,
            total_distance_meters=total_distance_meters,
            bcd_total_steps=bcd_total_steps,
            hourly_intervals=hourly_intervals,
            hourly_by_hour=hourly_by_hour,
            daily_history_list=daily_history_list,
        )


class StepCounterIO:
    """Manages requesting, fragment accumulation, and decoding of ABL-100 step counter notifications."""

    result: CancelableResult[StepCounterData] | None = None
    connection: ConnectionProtocol | None = None
    accumulator: bytearray = bytearray()
    expected_length: int = FALLBACK_EXPECTED_LENGTH
    peek: bool = True

    @staticmethod
    async def request(connection: ConnectionProtocol, peek: bool = False) -> StepCounterData:
        """Request step counter data from the watch.

        By default we close the transaction after the payload is received so the
        connection is left in a usable state for subsequent watch operations.
        """
        from gshock_api.watch_info import watch_info

        if not watch_info.hasStepCounter:
            logger.info(f"Step counter not supported on watch model: {watch_info.model}")
            return StepCounterData.unavailable()

        StepCounterIO.connection = connection
        StepCounterIO.peek = peek
        StepCounterIO.accumulator = bytearray()
        StepCounterIO.expected_length = FALLBACK_EXPECTED_LENGTH
        StepCounterIO.result = CancelableResult[StepCounterData]()

        # Handle 0x0011 is CASIO_DATA_REQUEST_SP
        await connection.write(0x0011, START_TRANSACTION_CMD)
        try:
            return await StepCounterIO.result.get_result()
        finally:
            StepCounterIO.result = None
            StepCounterIO.accumulator = bytearray()

    @staticmethod
    def on_drsp_received(data: bytes) -> None:
        """Handles length announcement or ACK notifications on the DRSP characteristic (handle 0x0011)."""
        if len(data) < 5:
            return
        command = data[0]
        category = data[1]
        if category != DRSP_CATEGORY_EXERCISE:
            return

        if command == 0x00:
            announced_length = data[2] | (data[3] << 8) | (data[4] << 16)
            if StepCounterIO.result is not None:
                StepCounterIO.expected_length = announced_length
                logger.debug(f"StepCounterIO: expected length announced = {announced_length}B")

    @staticmethod
    def on_received(data: bytes) -> None:
        """Accumulates incoming fragments and parses StepCounterData when full payload is received. If peek was set, do not end transaction."""
        if StepCounterIO.result is None:
            return

        StepCounterIO.accumulator.extend(data)
        logger.debug(
            f"StepCounterIO.on_received: accumulated={len(StepCounterIO.accumulator)}B / "
            f"expected={StepCounterIO.expected_length}B"
        )

        if len(StepCounterIO.accumulator) < StepCounterIO.expected_length:
            return

        # StepCounterIO.peek is True means we are peeking at the data, so we don't want to send the end transaction command. If it's False, we want to send the end transaction command to tell the watch we're done.
        if StepCounterIO.connection is not None and not StepCounterIO.peek:
            try:
                # Fire-and-forget end transaction command
                import asyncio
                asyncio.create_task(
                    StepCounterIO.connection.write(0x0011, END_TRANSACTION_CMD)
                )
            except Exception as e:
                logger.warning(f"Failed to send end transaction command: {e}")

        full_payload = bytes(StepCounterIO.accumulator)
        step_data = StepCounterIOFunctional.parse(full_payload)

        if step_data is not None:
            StepCounterIO.result.set_result(step_data)
        else:
            logger.warning(f"Failed to parse activity record from {len(full_payload)}B payload")
            StepCounterIO.result.set_result(StepCounterData.unavailable())
