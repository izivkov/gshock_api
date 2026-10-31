# Expand F-B100W protocol support (#20)

Head: `d1be0f4` (Refactor step formats and exercise profile handling)
Base: `main`
Commits: `a0b10bf` (Expand F-B100W protocol support), `d1be0f4` (Refactor step formats and exercise profile handling)
Diff vs `main`: 14 files, +372 / -7

## Summary

This PR adds protocol support for the F-B100W and corrects a few encodings that were wrong for all models. It covers:

- Weekday encoding in the current-time payload.
- One-time and snooze flags in the alarm flag byte.
- The exercise profile (step goal, height, weight) codec.
- A step-record decoder for the F-B100W.
- DST transaction commands.
- A watch capability that selects the step-record format per model.

Tests: `python -m unittest tests.test_code` runs 33 tests, all passing on this head.

## Changes

### Current time: weekday encoding (all models)

`iolib/time_io.py`: the weekday byte changed from `dt.weekday()` (Monday = 0) to `dt.isoweekday()` (Monday = 1, Sunday = 7).

Verified against 19 captured `SET_TIME` payloads from several models (BX2, BX3, ABL, DW-H5600). All 19 match `isoweekday()`, and none match `weekday()`.

Not yet verified: Sunday. None of the captures is dated on a Sunday, so the value 7 is inferred.

`tests/test_code.py`: the expected weekday for 2026-05-30 (Saturday) changed from 5 to 6.

### Alarms: one-time and snooze flags (all models)

`model/alarms.py`:

- `ONE_TIME_MASK = 0x20`, `SNOOZE_MASK = 0x10`. Flags are written only when the alarm is enabled, and one-time takes precedence over snooze.
- `AlarmDict` gains optional `oneTime` and `snooze` keys. Decoded alarm JSON includes both keys.
- The decoder notes that some models clear byte 1 on read-back. Captures confirm this: the app writes `0x40` and the read-back shows `0x00`.

The new tests (`TestFb100w.test_alarm_flags_snooze_onetime`) check that the encoder produces `0x50` for snooze, `0x60` for one-time, and `0xC0` for hourly chime. These tests confirm consistency with the mask constants. They do not confirm the watch's behavior. No capture in `test_data` contains the snooze or one-time bits.

### Exercise profile (F-B100W)

New files: `model/exercise.py`, `iolib/exercise_io.py`.

- `Exercise` is a frozen dataclass with `step_goal` (default 10000), `height`, and `weight`, plus `encode()` and `decode()`.
- Wire format (opcode `0x2D`):
  ```
  2D 00 GG GG GG GG HH HH WW WW
  GG = step goal, packed BCD, low digit pair first
  HH = height, packed BCD, each byte bit-inverted
  WW = weight, packed BCD, each byte bit-inverted
  ```
- `ExerciseIO.request()` reads the profile. `ExerciseIO.set_exercise()` writes it to handle `0x000E`.
- `Protocol.SETTING_FOR_EXERCISE = 0x2D` and `CASIO_SETTING_FOR_EXERCISE` are added.
- Message dispatcher: `GET_EXERCISE` and `SET_EXERCISE` senders, and the receiver for `CASIO_SETTING_FOR_EXERCISE`.

Test fixture: `2d000000010087fe8fff` decodes to step goal 10000, height 178, weight 70, and re-encodes to the same bytes.

Not verified: the watch's read response. The captures contain only writes, so the assumption that the response starts with `2D 00` is untested.

Not in this head: `GshockAPI` and protocol-level get/set methods for the exercise profile. Callers can use the `iolib` layer directly for now.

### F-B100W step records

New file: `iolib/fb100_step_counter_io.py`. `Fb100StepCounterIO.parse()` decodes a 400-byte step record:

- Header (BCD year, month, day, hour, minute, second).
- 24 hourly slots of five u16 buckets each, with `0xFFFE` as the empty sentinel.
- Seven daily summaries, each with steps and distance (u32, `0xFFFFFFFE` as the sentinel).
- Current steps, current distance, and a BCD total that matches the LCD.

`iolib/step_counter_io.py` picks the decoder by `watch_info.stepRecordFormat`. Other models keep the existing parser.

`model/step_counter_data.py`: docstring updated to cover F-B100W. No field changes.

Test: `TestFb100w.test_step_record_parse` runs against `test_data/fb100w_step_record.hex`. Expected values: 273 steps, 100 m, timestamp 2026-09-30 17:13:01.

### DST transactions (F-B100W)

New file: `iolib/dst_transaction_io.py`. Opcode `0x21` begin and end frames, with three transaction types:

- `WORLD_CITY = 1`
- `SWAP_HOME_WORLD = 2`
- `DST_STATE = 3`

Described in the module docstring as confirmed against full HCI captures of the official app. The `begin` and `end` frames are not exercised by the tests; only `encode` is.

### Watch model flags

`watch_info.py`:

- `StepRecordFormat` enum, with `F_B100` and `ABL_100` values, selected per model.
- `F_B100` and `ABL_100` are set to use their respective formats.

## Known issues to resolve before merge

1. **Alarms 2 to 5 are encoded from stale state.** `model/alarms.py` `from_json_alarm_secondary_alarms` uses `self.alarms[1:]`, which is the state from the last read. `main` uses `alarms_json[1:]`, the request. I tested this:
   - With no prior read, only the header `0x16` is sent, so alarms 2 to 5 are not written.
   - After a read, the previously read alarms are written instead of the requested ones.

   Fix: restore `alarms_json[1:]` and the `main` comment. With that fix, a snooze alarm 5 encodes as `0x50`.

2. **The new `TestFb100w` class sits after the `if __name__ == "__main__": unittest.main()` block.** Running `python tests/test_code.py` directly executes `unittest.main()` before the class is defined, so those tests are skipped. They run when the module is imported (for example `python -m unittest tests.test_code`). Move the guard to the end of the file.

3. **Unverified bit positions.** `SNOOZE_MASK = 0x10` and `ONE_TIME_MASK = 0x20` have no capture support. Confirm with a snooze alarm, a one-time alarm, and a disabled alarm set in the official app, and compare the captured `0x15` and `0x16` writes.

4. **Sunday weekday.** Confirm with a `SET_TIME` captured on a Sunday.

5. **Exercise read response.** Capture a notification sent in reply to a `0x2D` read.

6. **Naming and API divergence from `fb-100w`.** This PR uses `Exercise` and `ExerciseIO.set_exercise`. The `fb-100w` branch uses `ExerciseProfile`, `ExerciseIO.encode`, and `GshockAPI.get_exercise_profile` / `set_exercise_profile`. Pick one model name and one public API before merging, or the two branches will conflict.

7. **Whitespace-only changes.** Trailing spaces are removed in `time_io.py`, and `step_counter_io.py` has blank-line noise. These can be dropped to keep the diff focused.

## Reviewer checklist

- [ ] Fix alarm secondary-block encoding (issue 1).
- [ ] Move the `unittest.main()` guard (issue 2).
- [ ] Confirm the snooze and one-time bits against a capture (issue 3).
- [ ] Confirm Sunday as 7 (issue 4).
- [ ] Confirm the exercise read response (issue 5).
- [ ] Reconcile the exercise model and API with `fb-100w` (issue 6).
- [ ] Remove whitespace noise (issue 7).