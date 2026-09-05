# Kotlin Lifelog Porting Guide

This document describes the ABL-100 lifelog changes implemented in the Python
library and the corresponding work required in the Kotlin project.

The feature reads the watch's structured life-log record, preserves hourly
activity intensity, exposes distance components, and reports the decoded data
through `StepCounterData` and the step-counter example.

## Scope

The implementation adds:

- Five intensity buckets for each committed activity period.
- The three pending intensity buckets for the current period.
- The committed distance stack, in newest-first order.
- Existing current and pending distance totals.
- CLI output for per-period steps, intensity, and distance.

The activity records are hourly records. The five intensity values inside one
record are buckets of activity intensity, not five ten-minute time intervals.

## Files Changed

| Python file | Purpose | Kotlin equivalent |
| --- | --- | --- |
| `src/gshock_api/model/step_counter_data.py` | Public decoded lifelog data model | `StepCounterData.kt` or equivalent activity model |
| `src/gshock_api/iolib/step_counter_io.py` | Binary payload parser and BLE transfer handler | `StepCounterIo.kt` plus a lifelog parser |
| `src/examples/step_counter.py` | Human-readable summary and activity output | Kotlin sample/CLI application |
| `RELEASE_NOTES.md` | Release documentation | Kotlin project changelog or release notes |

No BLE request protocol changes are required for the new fields. The existing
step-counter transfer still supplies the complete payload; the additions are
parser and model changes.

## Data Model Changes

Add the following fields to the Kotlin equivalent of `StepCounterData`:

```kotlin
val hourlyIntensities: List<IntArray>
val pendingIntensity: IntArray
val committedDistances: List<Int>
```

Recommended semantics:

| Field | Meaning |
| --- | --- |
| `hourlyIntensities` | One five-value intensity array for each committed hourly activity record, oldest-to-newest according to the parser's record order. |
| `pendingIntensity` | Three raw intensity values for the current, not-yet-committed activity period. It may be empty for a truncated payload. |
| `committedDistances` | Distance components read from the distance stack at offset `246`, in newest-first order. |

The existing fields remain useful:

- `hourlyIntervals` contains the hourly record index, step total, and intensity.
- `distanceMeters` / `totalDistanceMeters` contains the current-day total at
  offset `378`.
- `pendingDistanceMeters` contains the current pending distance at offset
  `392`.
- `dailyDistances` contains the seven daily summary distances.

Use an immutable Kotlin representation where practical. For example, a
dedicated value type is clearer than an untyped map:

```kotlin
data class ActivityPeriod(
    val index: Int,
    val steps: Int?,
    val intensity: IntArray,
    val distanceMeters: Int?
)
```

## Binary Payload Layout

All multi-byte numeric values are little-endian.

| Offset | Size | Type | Meaning |
| ---: | ---: | --- | --- |
| `6` | variable | five `uint16` values per 10-byte record | Committed hourly activity intensity records |
| `246` | up to 72 | `uint16[]` | Committed distance stack, newest first |
| `318` | 56 | seven `(uint32 steps, uint32 distance)` pairs | Daily summaries |
| `374` | 4 | `uint32` | Current-day total steps |
| `378` | 4 | `uint32` | Current-day total distance in metres |
| `382` | 6 | three `uint16` values | Pending/current activity intensity |
| `392` | 4 | `uint32` | Pending/current activity distance in metres |
| `396` | 4 | packed BCD bytes | Total step count consistency value |

The activity-record region ends before the auxiliary/history data and is found
by reconciling the sum of the five-value records plus pending steps with the
current-day step total. Do not assume a fixed 144-record layout.

## Sentinel Handling

The watch uses these empty markers:

```kotlin
const val EMPTY_BUCKET = 0xFFFE
const val EMPTY_DAILY_VALUE = 0xFFFFFFFE.toInt()
```

For step totals, distance reconciliation, and display sums, ignore
`EMPTY_BUCKET`. Preserve the raw bucket values in the model if callers need to
distinguish an empty bucket from a real zero.

For daily summaries, treat a pair of `EMPTY_DAILY_VALUE` values as an unused
slot. A partially empty pair should produce a warning rather than silently
turning into a valid summary.

For truncated payloads, return the fields that can be decoded, leave missing
collections empty, and add a parser warning. The Kotlin parser should avoid
out-of-bounds reads by checking every offset before unpacking.

## Distance Parsing

The current-day total and pending distance do not directly provide the
individual hourly distances. To recover the committed components:

1. Read `totalDistance` from offset `378`.
2. Read `pendingDistance` from offset `392`.
3. Compute `committedTarget = totalDistance - pendingDistance`.
4. Read `uint16` values from offset `246` through offset `317`.
5. Skip `0xFFFE` values and accumulate components in order.
6. Stop when the accumulated sum equals `committedTarget`.
7. If the target cannot be reconciled, return an empty committed-distance list
   and record a warning.

If `committedTarget` is zero, the committed-distance list should be empty and
no warning is required.

## Intensity Parsing

For every committed activity record:

```kotlin
val buckets = IntArray(5) { bucketIndex ->
    readUInt16(payload, recordOffset + bucketIndex * 2)
}
val steps = buckets
    .filter { it != EMPTY_BUCKET }
    .sum()
```

The current pending period uses three buckets at offset `382`:

```kotlin
val pendingIntensity = IntArray(3) { index ->
    readUInt16(payload, 382 + index * 2)
}
```

The pending step total is the sum of non-empty pending buckets. It should be
included in the current hour's aggregate but not in the committed activity
record list.

## Kotlin File-by-File Work

### `StepCounterData.kt`

- Add `hourlyIntensities`.
- Add `pendingIntensity`.
- Add `committedDistances`.
- Keep defaults safe for unsupported and truncated records.
- Prefer a typed `ActivityPeriod` list over `List<Map<String, Any>>`.

### `StepCounterIo.kt` / lifelog parser

- Preserve the existing BLE request and fragment accumulation flow.
- Decode the fields in the layout above.
- Populate the new model fields in the same parse operation as steps and daily
  summaries.
- Preserve warnings when distance components cannot be reconciled.
- Keep the parser independent from console formatting.

### `MessageDispatcher.kt`

No new characteristic registration is needed solely for these fields if the
existing step-counter notification is already routed to `StepCounterIo`. Verify
that the complete payload reaches the parser before decoding.

### `GshockApi.kt`

No new public request method is required if the existing full-history method
already returns `StepCounterData`. Ensure the Kotlin API returns the enriched
model rather than reducing it to only the step total.

### Kotlin sample or CLI

Update the sample output to show:

- Hourly steps.
- Matching committed distance, when available.
- The five intensity buckets for each committed hourly record.
- Pending distance and three pending intensity buckets for the current hour.
- A placeholder such as `-` when a distance component is unavailable.

Do not label these records as ten-minute slots. They are hourly activity
records with five intensity buckets.

## Validation Checklist

Use a 400-byte fixture and verify:

1. A record with one activity period decodes five intensity values.
2. Pending intensity at `382` decodes three values.
3. A distance stack whose values sum to `totalDistance - pendingDistance`
   produces the expected committed list.
4. A zero committed target produces an empty list without a warning.
5. An unreconcilable distance stack produces a warning and no partial claim.
6. A truncated payload does not throw an index exception.
7. The sample output displays intensity and distance without changing the
   existing step totals.
