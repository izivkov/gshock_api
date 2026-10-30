import struct
from datetime import datetime
from typing import Final

from gshock_api.model.step_counter_data import StepCounterData

# F-B100W (module 3589) step counter record, captured 2026-09-30/10-04
HEADER_MARKER: Final[int] = 0x26
HEADER_SIZE: Final[int] = 6
ACTIVITY_RECORD_SIZE: Final[int] = 10
DAILY_SUMMARY_OFFSET: Final[int] = 318
DAILY_SUMMARY_COUNT: Final[int] = 7
DAILY_SUMMARY_SIZE: Final[int] = 8
CURRENT_STEPS_OFFSET: Final[int] = 374
CURRENT_DISTANCE_OFFSET: Final[int] = 378
PENDING_INTENSITY_OFFSET: Final[int] = 382
BCD_TOTAL_OFFSET: Final[int] = 396
SENTINEL_U16: Final[int] = 0xFFFE
SENTINEL_U32: Final[int] = 0xFFFFFFFE


def _bcd(byte: int) -> int:
    return (byte >> 4) * 10 + (byte & 0xF)


class Fb100StepCounterIO:
    """Decoder for the F-B100W step counter record (category 0x11)."""

    @staticmethod
    def parse(payload: bytes) -> StepCounterData | None:
        if not payload or payload[0] != HEADER_MARKER or len(payload) < 400:
            return None

        # Header: BCD YY MM DD hh mm ss
        year = 2000 + _bcd(payload[0])
        month = _bcd(payload[1])
        day = _bcd(payload[2])
        hour = _bcd(payload[3])
        minute = _bcd(payload[4])
        second = _bcd(payload[5])
        timestamp = datetime(year, month, day, hour, minute, second)

        u16 = lambda o: struct.unpack_from("<H", payload, o)[0]
        u32 = lambda o: struct.unpack_from("<I", payload, o)[0]

        # 24 hourly slots, 10 bytes each: 5 buckets of u16 steps
        hourly_steps = []
        for i in range(24):
            buckets = [u16(HEADER_SIZE + i * ACTIVITY_RECORD_SIZE + k * 2) for k in range(5)]
            if all(x == SENTINEL_U16 for x in buckets):
                hourly_steps.append(None)
            else:
                hourly_steps.append(sum(x for x in buckets if x != SENTINEL_U16))

        # 7 daily summaries: u32 steps, u32 distance
        daily_history = []
        daily_distances = []
        for d in range(DAILY_SUMMARY_COUNT):
            off = DAILY_SUMMARY_OFFSET + d * DAILY_SUMMARY_SIZE
            s, m = struct.unpack_from("<II", payload, off)
            daily_history.append(None if s == SENTINEL_U32 else s)
            daily_distances.append(None if m == SENTINEL_U32 else m)

        current_day_steps = u32(CURRENT_STEPS_OFFSET)
        if current_day_steps == SENTINEL_U32:
            current_day_steps = None

        distance_meters = u32(CURRENT_DISTANCE_OFFSET)
        if distance_meters == SENTINEL_U32:
            distance_meters = None

        # BCD total (matches LCD display)
        bcd_total_steps = None
        raw_bcd = payload[BCD_TOTAL_OFFSET:BCD_TOTAL_OFFSET + 4]
        if any(raw_bcd):
            bcd_total_steps = sum(_bcd(x) * (100 ** i) for i, x in enumerate(raw_bcd))

        return StepCounterData(
            timestamp=timestamp,
            day_of_week=timestamp.weekday(),
            month=month,
            day_of_month=day,
            hourly_steps=hourly_steps,
            daily_history=daily_history,
            daily_distances=daily_distances,
            current_day_steps=current_day_steps,
            raw=payload,
            distance_meters=distance_meters,
            bcd_total_steps=bcd_total_steps,
        )
