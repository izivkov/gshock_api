#!/usr/bin/env python3
"""Print a human-readable report for a 400-byte Casio life-log record."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

RECORD_SIZE = 400
EMPTY_U16 = 0xFFFE
EMPTY_U32 = 0xFFFFFFFE
TIMESTAMP_OFFSET = 0
CURRENT_DISTANCE_OFFSET = 246
DAILY_SUMMARIES_OFFSET = 318
CURRENT_STEPS_OFFSET = 374
CURRENT_DISTANCE_TOTAL_OFFSET = 378
PENDING_INTENSITY_OFFSET = 382
PENDING_DISTANCE_OFFSET = 392
BCD_TOTAL_OFFSET = 396
HISTORY_SLOTS = 24
INTENSITY_BUCKETS = 5


def u16(data: bytes, offset: int) -> int:
    """Read a little-endian unsigned 16-bit integer."""
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    """Read a little-endian unsigned 32-bit integer."""
    return struct.unpack_from("<I", data, offset)[0]


def bcd(byte: int) -> int:
    """Decode one packed-BCD byte."""
    high, low = divmod(byte, 16)
    if high > 9 or low > 9:
        raise ValueError(f"invalid BCD byte 0x{byte:02x}")
    return high * 10 + low


def decode_timestamp(data: bytes) -> dt.datetime:
    """Decode the six-byte timestamp at the start of a record."""
    values = [bcd(byte) for byte in data[:6]]
    return dt.datetime(2000 + values[0], *values[1:])


def decode_bcd_total(data: bytes) -> int:
    """Decode the four-byte little-endian packed-BCD total at offset 396."""
    return sum(bcd(data[396 + index]) * 100**index for index in range(4))


def read_input(argument: str) -> tuple[str, tuple[str, ...], bytes]:
    """Read a log file or a hexadecimal record supplied on the command line."""
    path = Path(argument)
    if path.is_file():
        lines = path.read_text(encoding="utf-8").splitlines()
        annotations = tuple(
            line.lstrip()[1:].strip()
            for line in lines
            if line.lstrip().startswith("#")
        )
        hexadecimal = "".join(
            line.strip()
            for line in lines
            if line.strip() and not line.lstrip().startswith("#")
        )
        label = str(path)
    else:
        hexadecimal = argument
        label = "command line"
        annotations = ()

    try:
        data = bytes.fromhex(hexadecimal)
    except ValueError:
        try:
            data = zlib.decompress(base64.b64decode(hexadecimal))
        except Exception as error:
            raise ValueError(f"{label}: invalid hexadecimal or base64 data") from error
    if len(data) != RECORD_SIZE:
        raise ValueError(f"{label}: expected {RECORD_SIZE} bytes, got {len(data)}")
    return label, annotations, data


@dataclass(frozen=True)
class Activity:
    """One committed hour or the current, uncommitted hour."""

    hour: dt.datetime
    intensity: tuple[int, int, int, int, int]

    @property
    def steps(self) -> int:
        """Return the sum of all five step-intensity buckets."""
        return sum(value for value in self.intensity if value != EMPTY_U16)


@dataclass(frozen=True)
class HistoryEntry:
    """One previous-day history slot; None means that component was overwritten."""

    time: dt.time
    first: int | None
    second: int | None

    @property
    def known_steps(self) -> int:
        """Return the portion of the slot that is still readable."""
        return (self.first or 0) + (self.second or 0)


@dataclass(frozen=True)
class DailySummary:
    """One dated entry from the daily-summary ring."""

    days_ago: int
    steps: int
    distance: int

@dataclass(frozen=True)
class PreviousDay:
    """Previous-day detail that has not yet been overwritten."""

    date: dt.date
    total_steps: int
    total_distance: int
    evening: tuple[Activity, ...]
    history: tuple[HistoryEntry, ...]
    rollover_residue: int
    overwritten_first: int
    overwritten_second: int

    @property
    def recovered_steps(self) -> int:
        """Return all previous-day steps that remain readable."""
        evening = sum(activity.steps for activity in self.evening)
        history = sum(entry.known_steps for entry in self.history)
        return evening + history + self.rollover_residue

    @property
    def fully_preserved(self) -> bool:
        """Return whether neither previous-day component array was overwritten."""
        return self.overwritten_first == 0 and self.overwritten_second == 0


@dataclass(frozen=True)
class Field:
    """A half-open byte range whose meaning is known."""

    start: int
    end: int
    name: str


@dataclass(frozen=True)
class Entry:
    """One lifelog entry (committed hour, history slot, or pending walk)."""

    timestamp: dt.datetime
    steps: int
    intensity: tuple[int, ...]  # nonzero buckets only
    approx: bool = False
    pending: bool = False


@dataclass(frozen=True)
class Lifelog:
    """The confidently decoded portions of a life-log record."""

    timestamp: dt.datetime
    raw: bytes
    total_steps: int
    total_distance: int
    bcd_total: int
    activities: tuple[Activity, ...]
    pending_intensity: tuple[int, int, int]
    committed_distances: tuple[int, ...]
    pending_distance: int
    auxiliary_offset: int
    auxiliary_a: tuple[int, ...]
    auxiliary_b: tuple[int, ...]
    daily_summaries: tuple[DailySummary, ...]
    today_history: tuple[HistoryEntry, ...]
    warnings: tuple[str, ...]
    previous_day: PreviousDay | None

    @classmethod
    def parse(cls, data: bytes) -> Lifelog:
        """Parse a validated 400-byte record."""
        if len(data) != RECORD_SIZE:
            raise ValueError(f"expected {RECORD_SIZE} bytes, got {len(data)}")
        warnings = []

        timestamp = decode_timestamp(data)
        total_steps = u32(data, CURRENT_STEPS_OFFSET)
        pending = tuple(
            u16(data, PENDING_INTENSITY_OFFSET + 2 * index)
            for index in range(3)
        )
        pending_steps = sum(clean(pending))
        record_end, warning = find_record_end(
            data, timestamp, total_steps, pending_steps
        )
        if warning:
            warnings.append(warning)

        activities = []
        for index, offset in enumerate(range(6, record_end, 10)):
            intensity = tuple(
                u16(data, offset + 2 * item)
                for item in range(INTENSITY_BUCKETS)
            )
            hour = timestamp.replace(minute=0, second=0, microsecond=0)
            hour -= dt.timedelta(hours=index + 1)
            activities.append(Activity(hour, intensity))

        distance = u32(data, CURRENT_DISTANCE_TOTAL_OFFSET)
        pending_distance = u32(data, PENDING_DISTANCE_OFFSET)
        distances, warning = distance_prefix(data, distance - pending_distance)
        if warning:
            warnings.append(warning)

        auxiliary_a = tuple(
            u16(data, record_end + 2 * index) for index in range(HISTORY_SLOTS)
        )
        auxiliary_b = tuple(
            u16(data, record_end + 50 + 2 * index) for index in range(HISTORY_SLOTS)
        )

        today_history: tuple[HistoryEntry, ...] = ()
        if timestamp.hour >= 18:
            today_history = tuple(
                HistoryEntry(
                    history_time(i),
                    auxiliary_a[i] if auxiliary_a[i] != EMPTY_U16 else 0,
                    auxiliary_b[i] if auxiliary_b[i] != EMPTY_U16 else 0,
                )
                for i in range(HISTORY_SLOTS)
            )

        summaries, summary_warnings = read_daily_summaries(data)
        warnings.extend(summary_warnings)

        previous_day = parse_previous_day(
            data,
            timestamp,
            record_end,
            auxiliary_a,
            auxiliary_b,
            summaries,
        )

        if (
            previous_day is not None
            and previous_day.fully_preserved
            and previous_day.recovered_steps != previous_day.total_steps
        ):
            warnings.append(
                "fully preserved previous day reconstructs "
                f"{previous_day.recovered_steps:,}, "
                f"expected {previous_day.total_steps:,}"
            )

        bcd_total = decode_bcd_total(data)
        if bcd_total != total_steps:
            warnings.append(
                f"BCD total {bcd_total:,} does not match steps {total_steps:,}"
            )
        reconstructed = sum(activity.steps for activity in activities) + pending_steps
        if timestamp.hour >= 18:
            reconstructed += sum(clean(auxiliary_a)) + sum(clean(auxiliary_b))
        if reconstructed != total_steps:
            warnings.append(
                f"step components reconstruct {reconstructed:,}, "
                f"expected {total_steps:,}"
            )

        return cls(
            timestamp=timestamp,
            raw=data,
            total_steps=total_steps,
            total_distance=distance,
            bcd_total=bcd_total,
            activities=tuple(activities),
            pending_intensity=pending,
            committed_distances=distances,
            pending_distance=pending_distance,
            auxiliary_offset=record_end,
            auxiliary_a=auxiliary_a,
            auxiliary_b=auxiliary_b,
            daily_summaries=summaries,
            today_history=today_history,
            warnings=tuple(warnings),
            previous_day=previous_day,
        )

    def lifelog_entries(self) -> list[Entry]:
        """Return sorted lifelog entries from the already-parsed fields."""
        entries: list[Entry] = []

        for activity in self.activities:
            if activity.steps:
                ts = activity.hour.replace(minute=0)
                entries.append(Entry(ts, activity.steps, clean(activity.intensity)))

        pending = clean(self.pending_intensity)
        if sum(pending):
            ts = self.timestamp.replace(minute=0, second=0, microsecond=0)
            entries.append(Entry(ts, sum(pending), pending, False, True))

        if self.timestamp.hour >= 18:
            for hist in self.today_history:
                if hist.known_steps:
                    ts = dt.datetime.combine(
                        self.timestamp.date(), hist.time
                    )
                    entries.append(Entry(ts, hist.known_steps, ()))

        if self.previous_day is not None:
            prev = self.previous_day
            for activity in prev.evening:
                if activity.steps:
                    ts = activity.hour.replace(minute=0)
                    entries.append(Entry(ts, activity.steps, clean(activity.intensity)))
            for hist in prev.history:
                if hist.known_steps:
                    ts = dt.datetime.combine(prev.date, hist.time)
                    entries.append(Entry(ts, hist.known_steps, ()))
            if prev.rollover_residue:
                ts = dt.datetime.combine(prev.date, dt.time(21, 0))
                entries.append(Entry(ts, prev.rollover_residue, (), approx=True))

        entries.sort(key=lambda e: e.timestamp)
        return entries


def read_daily_summaries(
    data: bytes,
) -> tuple[tuple[DailySummary, ...], tuple[str, ...]]:
    """Decode daily summaries without collapsing empty date slots."""
    summaries = []
    warnings = []
    slot_count = (CURRENT_STEPS_OFFSET - DAILY_SUMMARIES_OFFSET) // 8
    for index in range(slot_count):
        offset = DAILY_SUMMARIES_OFFSET + 8 * index
        steps = u32(data, offset)
        distance = u32(data, offset + 4)
        steps_empty = steps == EMPTY_U32
        distance_empty = distance == EMPTY_U32
        if steps_empty and distance_empty:
            continue
        if steps_empty != distance_empty:
            warnings.append(f"daily summary slot {index + 1} is only half empty")
            continue
        summaries.append(DailySummary(index + 1, steps, distance))
    return tuple(summaries), tuple(warnings)


def parse_previous_day(
    data: bytes,
    timestamp: dt.datetime,
    record_end: int,
    auxiliary_a: tuple[int, ...],
    auxiliary_b: tuple[int, ...],
    summaries: tuple[DailySummary, ...],
) -> PreviousDay | None:
    """Recover the previous-day detail that precedes the overwrite boundary."""
    if not timestamp.hour < 18:
        return None
    summary = next((item for item in summaries if item.days_ago == 1), None)
    if summary is None:
        return None

    previous_date = timestamp.date() - dt.timedelta(days=1)
    evening = []
    for index in range(3):
        offset = record_end + 100 + 10 * index
        intensity = tuple(
            u16(data, offset + 2 * item)
            for item in range(INTENSITY_BUCKETS)
        )
        hour = dt.datetime.combine(previous_date, dt.time(19 - index))
        evening.append(Activity(hour, intensity))

    first_start = record_end + 130
    second_start = record_end + 180
    safe_first = max(
        0, min(HISTORY_SLOTS, (CURRENT_DISTANCE_OFFSET - first_start) // 2)
    )
    safe_second = max(
        0, min(HISTORY_SLOTS, (CURRENT_DISTANCE_OFFSET - second_start) // 2)
    )
    history = []
    for index in range(HISTORY_SLOTS):
        first = u16(data, first_start + 2 * index) if index < safe_first else None
        second = u16(data, second_start + 2 * index) if index < safe_second else None
        if first == EMPTY_U16:
            first = 0
        if second == EMPTY_U16:
            second = 0
        time = history_time(index)
        history.append(HistoryEntry(time, first, second))

    residue = sum(clean(auxiliary_a)) + sum(clean(auxiliary_b))
    total_steps = summary.steps
    total_distance = summary.distance
    return PreviousDay(
        date=previous_date,
        total_steps=total_steps,
        total_distance=total_distance,
        evening=tuple(evening),
        history=tuple(history),
        rollover_residue=residue,
        overwritten_first=24 - safe_first,
        overwritten_second=24 - safe_second,
    )


def _front_sum(data: bytes, start: int, end: int) -> int:
    """Sum steps in the front-record region as structured 10-byte records."""
    total = 0
    for offset in range(start, end, 10):
        for index in range(INTENSITY_BUCKETS):
            value = u16(data, offset + 2 * index)
            if value != EMPTY_U16:
                total += value
    return total


def _history_sum(data: bytes, record_end: int) -> int:
    """Sum non-empty slots across both M1 and M2 history arrays."""
    total = 0
    for base in (record_end, record_end + 50):
        for index in range(HISTORY_SLOTS):
            value = u16(data, base + 2 * index)
            if value != EMPTY_U16:
                total += value
    return total


def _score_candidate(
    data: bytes, timestamp: dt.datetime, candidate: int, target: int
) -> int:
    """Return |target - reconstruction| for a candidate boundary."""
    front = _front_sum(data, 6, candidate)
    if timestamp.hour >= 18:
        recon = front + _history_sum(data, candidate)
    else:
        recon = front
    return abs(target - recon)


def find_record_end(
    data: bytes, timestamp: dt.datetime, total: int, pending: int
) -> tuple[int, str | None]:
    """Locate hourly records and warn when the boundary is not proven."""
    committed_target = total - pending

    if timestamp.hour < 18:
        expected = 6 + 10 * max(0, timestamp.hour - 6)
        if _front_sum(data, 6, expected) + pending == total:
            return expected, None

    scored = [
        (candidate, _score_candidate(data, timestamp, candidate, committed_target))
        for candidate in range(6, 130, 10)
    ]
    best_score = min(score for _, score in scored)
    chosen = min(candidate for candidate, score in scored if score == best_score)

    if best_score:
        # When the best boundary still mismatches, try every candidate
        # against the full reconstruction (including M1/M2 when hour>=18)
        # to see if a different boundary produces a perfect match.
        perfect = [
            candidate
            for candidate, _ in scored
            if _score_candidate(data, timestamp, candidate, committed_target) == 0
        ]
        if perfect:
            chosen = min(perfect)
        else:
            warning = (
                f"record boundary @{chosen} is heuristic; "
                f"best reconciliation differs by {best_score:,} steps"
            )
            return chosen, warning

    same_score = [c for c, s in scored if s == best_score]
    if len(same_score) > 1:
        choices = ", ".join(str(offset) for offset in same_score)
        return chosen, f"record boundary is ambiguous among offsets {choices}"
    return chosen, None


def distance_prefix(
    data: bytes, target: int
) -> tuple[tuple[int, ...], str | None]:
    """Return an exact distance prefix, or no claimed fields and a warning."""
    if target < 0:
        return (), f"pending distance exceeds total distance by {-target:,} m"
    if target == 0:
        return (), None

    values = []
    total = 0
    for offset in range(
        CURRENT_DISTANCE_OFFSET, DAILY_SUMMARIES_OFFSET, 2
    ):
        value = u16(data, offset)
        values.append(value)
        total += value
        if total == target:
            return tuple(values), None
        if total > target:
            break
    return (), f"distance components do not reconcile to {target:,} m"


def clean(values: tuple[int, ...]) -> tuple[int, ...]:
    """Replace the protocol's empty marker with zero for display and sums."""
    return tuple(0 if value == EMPTY_U16 else value for value in values)


def history_time(index: int) -> dt.time:
    """Map a component-array index to its tentative half-hour slot."""
    slot = (index + 10) % HISTORY_SLOTS
    value = dt.datetime.min + dt.timedelta(hours=6, minutes=30 * slot)
    return value.time()



def known_fields(log: Lifelog) -> tuple[Field, ...]:
    """List every byte range currently understood by the parser."""
    end = log.auxiliary_offset
    fields = [
        Field(TIMESTAMP_OFFSET, 6, "timestamp"),
        Field(6, end, "current hourly intensity"),
        Field(end, end + 48, "auxiliary component A"),
        Field(end + 50, end + 98, "auxiliary component B"),
        Field(
            CURRENT_DISTANCE_OFFSET,
            CURRENT_DISTANCE_OFFSET + 2 * len(log.committed_distances),
            "distance components",
        ),
        Field(DAILY_SUMMARIES_OFFSET, CURRENT_STEPS_OFFSET, "daily summaries"),
        Field(CURRENT_STEPS_OFFSET, PENDING_INTENSITY_OFFSET, "current totals"),
        Field(
            PENDING_INTENSITY_OFFSET,
            PENDING_INTENSITY_OFFSET + 6,
            "pending intensity",
        ),
        Field(PENDING_DISTANCE_OFFSET, BCD_TOTAL_OFFSET, "pending distance"),
        Field(BCD_TOTAL_OFFSET, RECORD_SIZE, "BCD step total"),
    ]

    if log.previous_day is not None:
        previous = log.previous_day
        safe_first = 24 - previous.overwritten_first
        safe_second = 24 - previous.overwritten_second
        fields.extend(
            (
                Field(end + 100, end + 130, "previous evening intensity"),
                Field(end + 130, end + 130 + 2 * safe_first, "previous component A"),
                Field(end + 180, end + 180 + 2 * safe_second, "previous component B"),
            )
        )

    return tuple(field for field in fields if field.start < field.end)


def unknown_fields(log: Lifelog) -> tuple[Field, ...]:
    """Return the complement of known_fields(); this is the sole unknown registry."""
    claimed = [False] * RECORD_SIZE
    for field in known_fields(log):
        for offset in range(max(0, field.start), min(RECORD_SIZE, field.end)):
            claimed[offset] = True

    unknown = []
    start = None
    for offset, is_claimed in enumerate((*claimed, True)):
        if not is_claimed and start is None:
            start = offset
        elif is_claimed and start is not None:
            unknown.append(Field(start, offset, "unknown"))
            start = None
    return tuple(unknown)


def print_unknown(log: Lifelog) -> None:
    """Print undecoded ranges in hexadecimal and little-endian integer form."""
    fields = unknown_fields(log)
    print("\n  Unknown fields")
    if not fields:
        print("    none")
        return

    for field in fields:
        raw = log.raw[field.start : field.end]
        print(f"    @{field.start:03d}-{field.end - 1:03d} ({len(raw)} bytes)")
        for offset in range(0, len(raw), 16):
            chunk = raw[offset : offset + 16]
            print(f"      hex: {' '.join(f'{byte:02x}' for byte in chunk)}")
        if field.start % 2 == 0 and len(raw) % 2 == 0:
            values = struct.unpack(f"<{len(raw) // 2}H", raw)
            for offset in range(0, len(values), 8):
                chunk = ", ".join(str(value) for value in values[offset : offset + 8])
                print(f"      u16: {chunk}")


def print_previous_day(previous: PreviousDay) -> None:
    """Render preserved previous-day entries and their recovery status."""
    evening = [activity for activity in previous.evening if activity.steps]
    recovered = previous.recovered_steps
    complete = previous.fully_preserved and recovered == previous.total_steps

    print(f"\n  Previous day detail ({previous.date})")
    print(
        f"    Stored total: {previous.total_steps:,} steps, "
        f"{previous.total_distance:,} m"
    )
    status = "complete" if complete else "partial"
    print(f"    Recovered:    {recovered:,}/{previous.total_steps:,} steps ({status})")
    if not complete:
        print(
            "    Overwritten:  "
            f"{previous.overwritten_first} first-component slots, "
            f"{previous.overwritten_second} second-component slots"
        )

    for entry in sorted(previous.history, key=lambda item: item.time):
        if not entry.known_steps:
            continue
        exact = entry.first is not None and entry.second is not None
        first = "overwritten" if entry.first is None else str(entry.first)
        second = "overwritten" if entry.second is None else str(entry.second)
        steps = (
            f"{entry.known_steps:,}"
            if exact
            else f"at least {entry.known_steps:,}"
        )
        print(
            f"    {entry.time:%H:%M}  {steps} steps  "
            f"components=({first}, {second})"
        )

    for activity in sorted(evening, key=lambda item: item.hour):
        print(
            f"    {activity.hour:%H:00}  {activity.steps:>5,} steps  "
            f"intensity={clean(activity.intensity)}"
        )
    if previous.rollover_residue:
        print(
            f"    21:00  {previous.rollover_residue:>5,} steps  "
            "[rollover residue; time inferred]"
        )


def print_current_activity(log: Lifelog) -> None:
    """Render committed and pending activity for the current day."""
    active = [activity for activity in reversed(log.activities) if activity.steps]
    print("\n  Hourly activity (five intensity buckets, lowest to highest)")
    if not active:
        print("    none committed")
    for activity in active:
        print(
            f"    {activity.hour:%H:00}  {activity.steps:>5,} steps  "
            f"intensity={clean(activity.intensity)}"
        )

    pending_steps = sum(clean(log.pending_intensity))
    if pending_steps:
        print(
            f"    {log.timestamp:%H:00}  {pending_steps:>5,} steps  "
            f"intensity={clean(log.pending_intensity)}  [pending]"
        )


def print_distance(log: Lifelog) -> None:
    """Render current-day distance components."""
    print("\n  Distance components (metres, newest first)")
    print(f"    committed={log.committed_distances or 'none'}")
    print(f"    pending={log.pending_distance:,}")


def print_auxiliary_history(log: Lifelog) -> None:
    """Render auxiliary component arrays when they are not rollover residue."""
    history_is_current = log.timestamp.hour >= 18
    entries = []
    for index, (first, second) in enumerate(
        zip(log.auxiliary_a, log.auxiliary_b)
    ):
        first = 0 if first == EMPTY_U16 else first
        second = 0 if second == EMPTY_U16 else second
        if first or second:
            entries.append((history_time(index), first, second))

    if not entries or (not history_is_current and log.previous_day is not None):
        return
    heading = "Current-day history" if history_is_current else "Auxiliary history"
    note = (
        "30-minute mapping"
        if history_is_current
        else "tentative; not in today's total"
    )
    print(f"\n  {heading} @{log.auxiliary_offset} ({note})")
    for time, first, second in entries:
        print(
            f"    {time:%H:%M}  {first + second:>5,}  "
            f"components=({first}, {second})"
        )


def print_daily_summaries(log: Lifelog) -> None:
    """Render dated summary-ring entries not expanded as previous-day detail."""
    summaries = tuple(
        summary
        for summary in log.daily_summaries
        if log.previous_day is None or summary.days_ago != 1
    )
    if not summaries:
        return

    print("\n  Earlier daily summaries")
    for summary in summaries:
        date = log.timestamp.date() - dt.timedelta(days=summary.days_ago)
        print(
            f"    {date}: {summary.steps:,} steps, "
            f"{summary.distance:,} m"
        )


def print_report(
    label: str, annotations: tuple[str, ...], log: Lifelog
) -> None:
    """Render a parsed record for a human reader."""
    committed_steps = sum(activity.steps for activity in log.activities)
    pending_steps = sum(clean(log.pending_intensity))
    history_steps = sum(clean(log.auxiliary_a)) + sum(clean(log.auxiliary_b))
    history_is_current = log.timestamp.hour >= 18
    step_check = committed_steps + pending_steps
    if history_is_current:
        step_check += history_steps
    distance_check = sum(log.committed_distances) + log.pending_distance

    print(label)
    if annotations:
        print("  Notes:")
        for annotation in annotations:
            print(f"    {annotation}")
    print(f"  Captured:  {log.timestamp:%Y-%m-%d %H:%M:%S}")
    print(f"  Steps:     {log.total_steps:,}")
    print(f"  Distance:  {log.total_distance:,} m")
    print(
        "  Integrity: "
        f"steps {step_check:,}/{log.total_steps:,} "
        f"({'OK' if step_check == log.total_steps else 'MISMATCH'}), "
        f"distance {distance_check:,}/{log.total_distance:,} "
        f"({'OK' if distance_check == log.total_distance else 'MISMATCH'}), "
        f"BCD {'OK' if log.bcd_total == log.total_steps else 'MISMATCH'}"
    )

    if log.warnings:
        print("  Warnings:")
        for warning in log.warnings:
            print(f"    - {warning}")

    print_current_activity(log)
    print_distance(log)
    if log.previous_day is not None:
        print_previous_day(log.previous_day)
    print_auxiliary_history(log)
    print_daily_summaries(log)
    print_unknown(log)


def main() -> None:
    """Parse command-line inputs and print reports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input", nargs="+", help="log file or 400-byte hexadecimal record"
    )
    arguments = parser.parse_args()

    for index, argument in enumerate(arguments.input):
        if index:
            print()
        try:
            label, annotations, data = read_input(argument)
            print_report(label, annotations, Lifelog.parse(data))
        except (OSError, ValueError) as error:
            parser.error(str(error))


if __name__ == "__main__":
    main()
