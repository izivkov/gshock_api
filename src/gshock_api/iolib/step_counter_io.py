import asyncio
import struct
from datetime import datetime
from typing import Final

from gshock_api.cancelable_result import CancelableResult
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.logger import logger
from gshock_api.model.step_counter_data import StepCounterData

FALLBACK_EXPECTED_LENGTH: Final[int] = 400
DRSP_CATEGORY_EXERCISE: Final[int] = 0x11
START_TRANSACTION_CMD: Final[bytes] = bytes([0x00, DRSP_CATEGORY_EXERCISE, 0x00, 0x00, 0x00])
END_TRANSACTION_CMD: Final[bytes] = bytes([0x04, DRSP_CATEGORY_EXERCISE, 0x00, 0x00, 0x00])

PACKET_HEADER_MARKER: Final[int] = 0x26
BLE_HANDLE_DRSP: Final[int] = 0x0011
SENTINEL_BUCKET_VALUE: Final[int] = 0xFFFE
SENTINEL_DAILY_VALUE: Final[int] = 0xFFFFFFFE
BCD_BASE: Final[int] = 16
BCD_MAX_DIGIT: Final[int] = 9
BASE_CENTURY_YEAR: Final[int] = 2000
ACTIVITY_SCAN_LIMIT: Final[int] = 146


def _decode_bcd(byte: int) -> int:
    high, low = divmod(byte, BCD_BASE)
    if high > BCD_MAX_DIGIT or low > BCD_MAX_DIGIT:
        raise ValueError(f"invalid BCD byte 0x{byte:02x}")
    return high * 10 + low


class StepCounterIOFunctional:
    """Pure functional core for decoding ABL-100WE step counter (life-log) records."""

    HEADER_SIZE: Final[int] = 6
    ACTIVITY_RECORD_SIZE: Final[int] = 10
    ACTIVITY_BUCKET_COUNT: Final[int] = 5
    HISTORY_SLOT_COUNT: Final[int] = 24
    DAILY_SUMMARY_OFFSET: Final[int] = 318
    DAILY_SUMMARY_COUNT: Final[int] = 7
    DAILY_SUMMARY_SIZE: Final[int] = 8
    COMMITTED_DISTANCE_OFFSET: Final[int] = 246
    COMMITTED_DISTANCE_END: Final[int] = 318
    CURRENT_STEPS_OFFSET: Final[int] = 374
    CURRENT_DISTANCE_OFFSET: Final[int] = 378
    PENDING_INTENSITY_OFFSET: Final[int] = 382
    PENDING_DISTANCE_OFFSET: Final[int] = 392
    BCD_TOTAL_OFFSET: Final[int] = 396

    @staticmethod
    def parse(payload: bytes) -> StepCounterData | None:
        if not payload or payload[0] != PACKET_HEADER_MARKER:
            return None

        warnings: list[str] = []

        # ABL records store month/day/time as packed BCD. The final header byte
        # is a status/reserved value rather than part of the timestamp.
        timestamp: datetime | None = None
        day_of_week: int | None = None
        month: int | None = None
        day_of_month: int | None = None
        if len(payload) >= 6:
            try:
                year = BASE_CENTURY_YEAR + _decode_bcd(payload[0])
                month = _decode_bcd(payload[1])
                day_of_month = _decode_bcd(payload[2])
                hour = _decode_bcd(payload[3])
                minute = _decode_bcd(payload[4])
                second = _decode_bcd(payload[5])
                timestamp = datetime(year, month, day_of_month, hour, minute, second)
            except ValueError:
                warnings.append("invalid BCD timestamp in step counter header")

        current_day_offset = StepCounterIOFunctional.CURRENT_STEPS_OFFSET
        current_day_steps = (
            struct.unpack_from("<I", payload, current_day_offset)[0]
            if len(payload) >= current_day_offset + 4
            else None
        )

        pending_steps = 0
        pending_intensity: tuple[int, ...] = ()
        if len(payload) >= StepCounterIOFunctional.PENDING_INTENSITY_OFFSET + 6:
            pending_intensity = struct.unpack_from(
                "<3H", payload, StepCounterIOFunctional.PENDING_INTENSITY_OFFSET
            )
            pending_steps = sum(value for value in pending_intensity if value != SENTINEL_BUCKET_VALUE)

        # Activity records are variable-length 10-byte records. Find the
        # boundary by reconciling their bucket sums with today's total.
        record_end = StepCounterIOFunctional.HEADER_SIZE
        if current_day_steps is not None:
            candidates: list[tuple[int, int]] = []
            for end in range(6, ACTIVITY_SCAN_LIMIT, StepCounterIOFunctional.ACTIVITY_RECORD_SIZE):
                front_total = 0
                for offset in range(6, end, StepCounterIOFunctional.ACTIVITY_RECORD_SIZE):
                    buckets = struct.unpack_from("<5H", payload, offset)
                    front_total += sum(value for value in buckets if value != SENTINEL_BUCKET_VALUE)
                candidates.append((abs(current_day_steps - pending_steps - front_total), end))
            record_end = min(candidates)[1]

        activity_steps: list[int | None] = []
        hourly_intensities: list[tuple[int, int, int, int, int]] = []
        hourly_intervals: list[dict] = []
        for index, offset in enumerate(
            range(6, record_end, StepCounterIOFunctional.ACTIVITY_RECORD_SIZE)
        ):
            buckets = struct.unpack_from("<5H", payload, offset)
            steps = sum(value for value in buckets if value != SENTINEL_BUCKET_VALUE)
            activity_steps.append(steps or None)
            hourly_intensities.append(buckets)
            hourly_intervals.append(
                {
                    "index": index,
                    "start_minute": 0,
                    "end_minute": 59,
                    "steps": steps or None,
                    "intensity": buckets,
                }
            )

        # Seven daily summaries occupy 8 bytes each: uint32 steps followed by
        # uint32 distance.  The 0xFFFFFFFE pair means an unused slot.
        daily_history: list[int | None] = []
        daily_distances: list[int | None] = []
        for index in range(StepCounterIOFunctional.DAILY_SUMMARY_COUNT):
            offset = StepCounterIOFunctional.DAILY_SUMMARY_OFFSET + index * StepCounterIOFunctional.DAILY_SUMMARY_SIZE
            if offset + StepCounterIOFunctional.DAILY_SUMMARY_SIZE > len(payload):
                break
            steps, distance = struct.unpack_from("<2I", payload, offset)
            if steps == SENTINEL_DAILY_VALUE and distance == SENTINEL_DAILY_VALUE:
                daily_history.append(None)
                daily_distances.append(None)
            else:
                daily_history.append(None if steps == SENTINEL_DAILY_VALUE else steps)
                daily_distances.append(None if distance == SENTINEL_DAILY_VALUE else distance)

        if current_day_steps == SENTINEL_DAILY_VALUE:
            current_day_steps = None

        distance_meters = None
        pending_distance_meters = None
        total_distance_meters = None
        bcd_total_steps = None
        committed_distances: list[int] = []

        if len(payload) < current_day_offset + 4:
            warnings.append("step record truncated; missing trailing history fields")

        if len(payload) >= StepCounterIOFunctional.CURRENT_DISTANCE_OFFSET + 4:
            distance_meters = struct.unpack_from("<I", payload, StepCounterIOFunctional.CURRENT_DISTANCE_OFFSET)[0]
            total_distance_meters = distance_meters

        if len(payload) >= StepCounterIOFunctional.PENDING_DISTANCE_OFFSET + 4:
            pending_distance_meters = struct.unpack_from("<I", payload, StepCounterIOFunctional.PENDING_DISTANCE_OFFSET)[0]

        if (
            distance_meters is not None
            and pending_distance_meters is not None
            and distance_meters >= pending_distance_meters
        ):
            committed_target = distance_meters - pending_distance_meters
            distance_sum = 0
            if committed_target:
                for offset in range(
                    StepCounterIOFunctional.COMMITTED_DISTANCE_OFFSET,
                    StepCounterIOFunctional.COMMITTED_DISTANCE_END,
                    2,
                ):
                    value = struct.unpack_from("<H", payload, offset)[0]
                    if value == SENTINEL_BUCKET_VALUE:
                        continue
                    committed_distances.append(value)
                    distance_sum += value
                    if distance_sum == committed_target:
                        break
                    if distance_sum > committed_target:
                        committed_distances = []
                        break
            if committed_target and distance_sum != committed_target:
                committed_distances = []
                warnings.append(
                    f"distance components do not reconcile to {committed_target:,} m"
                )

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
        hourly_steps = activity_steps
        hourly_by_hour: list[int | None] = [None] * 24
        if timestamp is not None:
            for index, steps in enumerate(activity_steps):
                if steps is not None:
                    hour = (timestamp.hour - index - 1) % 24
                    hourly_by_hour[hour] = steps
            if pending_steps:
                hourly_by_hour[timestamp.hour] = pending_steps

        # Daily history as list of dicts: days_ago=1 is most recent previous day
        daily_history_list = [{"days_ago": i + 1, "steps": v} for i, v in enumerate(daily_history)]

        return StepCounterData(
            timestamp=timestamp,
            day_of_week=day_of_week,
            month=month,
            day_of_month=day_of_month,
            hourly_steps=hourly_steps,
            daily_history=daily_history,
            daily_distances=daily_distances,
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
            hourly_intensities=hourly_intensities,
            pending_intensity=pending_intensity,
            committed_distances=committed_distances,
        )


class StepCounterIO:
    """Manages requesting, fragment accumulation, and decoding of ABL-100 step counter notifications."""

    result: CancelableResult[StepCounterData] | None = None
    connection: ConnectionProtocol | None = None
    accumulator: bytearray = bytearray()
    expected_length: int = FALLBACK_EXPECTED_LENGTH
    peek: bool = True
    _end_txn_task: asyncio.Task | None = None

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
        await connection.write(BLE_HANDLE_DRSP, START_TRANSACTION_CMD)
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
    def _log_end_txn_failure(task: asyncio.Task) -> None:
        """Done-callback for the end-transaction task. Guards against calling
        exception() on a cancelled task (which raises CancelledError instead of
        returning a value) and fetches the exception only once."""
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.warning(f"Failed to send end transaction command: {exc}")

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
                StepCounterIO._end_txn_task = asyncio.create_task(
                    StepCounterIO.connection.write(BLE_HANDLE_DRSP, END_TRANSACTION_CMD)
                )
                StepCounterIO._end_txn_task.add_done_callback(StepCounterIO._log_end_txn_failure)
            except Exception as e:
                logger.warning(f"Failed to schedule end transaction task: {e}")

        full_payload = bytes(StepCounterIO.accumulator)
        step_data = StepCounterIOFunctional.parse(full_payload)

        if step_data is not None:
            StepCounterIO.result.set_result(step_data)
        else:
            logger.warning(f"Failed to parse activity record from {len(full_payload)}B payload")
            StepCounterIO.result.set_result(StepCounterData.unavailable())