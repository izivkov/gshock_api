# fb-100w compared with main

Branch: `fb-100w` (origin/fb-100w)
Base: `main` (origin/main), merge base `da955e1`
Diff: 14 files, +293 / -23

## Summary

`fb-100w` adds the following to `main`:

- Exercise profile get and set (opcode `0x2D`) for watches that report one (`ABL_100`, `F_B100`).
- A weekday encoding fix in the current-time payload.
- One-time and snooze flags in the alarm flag byte.
- An alarm 5 mode helper, `apply_alarm5_mode`, used by the alarm encoder.
- A `hasExcersiseProfile` model flag, exposed on `WatchInfo`.
- An exercise profile example in `src/examples/api_tests.py`.

This branch has one blocking regression and one missing feature. See "Issues to resolve before merge."

## Changes by file

| File | Change |
|---|---|
| `casio_constants.py` | Adds `CASIO_SETTING_FOR_EXERCISE` (0x2D) |
| `iolib/packet.py` | Adds `Protocol.SETTING_FOR_EXERCISE` (0x2D) |
| `iolib/exercise_io.py` | New. Exercise codec and read/write IO |
| `model/exercise_profile.py` | New. `ExerciseProfile` dataclass |
| `message_dispatcher.py` | Adds `GET_EXERCISE`, `SET_EXERCISE`, and the `CASIO_SETTING_FOR_EXERCISE` receiver |
| `protocols/watch_protocol.py` | Adds abstract `get_exercise_profile` and `set_exercise_profile` |
| `protocols/standard_protocol.py` | Implements both methods |
| `gshock_api.py` | Adds `get_exercise_profile()` and `set_exercise_profile(profile)` |
| `watch_info.py` | Adds `hasExcersiseProfile` (True for `ABL_100` and `F_B100`) and its property |
| `iolib/time_io.py` | Weekday byte: `weekday()` becomes `isoweekday()`; whitespace cleanup |
| `iolib/alarms_io.py` | Applies `apply_alarm5_mode` in `prepare_watch_commands_set` |
| `model/alarms.py` | Adds one-time and snooze flags, `apply_alarm5_mode`, and the decoder fields |
| `iolib/step_counter_io.py` | Blank lines only. No functional change |
| `src/examples/api_tests.py` | Adds `test_exercise_profile`, which runs when the model has the flag |

## Details

### Exercise profile

- `ExerciseProfile`: `step_goal` (default 10000), `height`, `weight`.
- Wire format, validated against captures:
  ```
  2D 00 GG GG GG GG HH HH WW WW
  GG = step goal, packed BCD, low digit pair first
  HH = height, packed BCD, each byte bit-inverted
  WW = weight, packed BCD, each byte bit-inverted
  ```
  For example, `2D00005002008AFEAAFF` decodes to step goal 25000, height 175, and weight 55. `2D00008000008FFE9AFF` decodes to 8000, 170, and 65.
- `ExerciseIO.request()` sends the read request and waits for the response.
- `ExerciseIO.send_to_watch_set()` merges the incoming values with the last known profile, then writes to handle `0x000E`. It requires `ExerciseIO.connection` to be set, which happens only after a read.
- `WatchProtocol` gains two abstract methods. Any subclass other than `StandardProtocol` (which covers `AnalogueProtocol` and `MipProtocol`) must implement them.
- Not verified: the watch's read response. The captures contain only writes, so the `2D 00` response prefix is an assumption.

### Weekday encoding

- `dt.weekday()` (Monday = 0 … Sunday = 6) is replaced with `dt.isoweekday()` (Monday = 1 … Sunday = 7).
- Verified against 19 captured `SET_TIME` payloads from several models (BX2, BX3, ABL, DW-H5600). All 19 match `isoweekday()`.
- Not verified: Sunday = 7. No capture is dated on a Sunday.

### Alarm flags

- Masks: `ONE_TIME_MASK = 0x20`, `SNOOZE_MASK = 0x10`. Existing: `ENABLED = 0x40`, `HOURLY_CHIME = 0x80`.
- Flags are written only when the alarm is enabled. One-time takes precedence over snooze.
- `AlarmDict` gains optional `oneTime` and `snooze` keys. Decoded alarm JSON always includes both keys, `false` unless the bits are set.
- The decoder comment notes that some models clear byte 1 on read-back. The captures confirm this.
- Not verified: neither mask appears in any capture. The values are assumptions.

### Alarm 5 mode

- `apply_alarm5_mode(alarms, snooze=True)` returns a copy of the list. Index 4 (alarm 5) is set to snooze, or to one-time when `snooze=False`. Other alarms are unchanged.
- `prepare_watch_commands_set` reads an optional top-level `"snoozeAlarm5"` key (default `true`) and applies the helper before encoding.
- Alarm 5 is the only alarm that can snooze (per device testing).

### Model flag

- `hasExcersiseProfile` is set to `True` for `ABL_100` and `F_B100`. The name contains a typo, and it is used consistently on this branch. Renaming it later would be a breaking change.

## Issues to resolve before merge

1. **Alarms 2 to 5 are encoded from stale state (regression).** `model/alarms.py` `from_json_alarm_secondary_alarms` uses `self.alarms[1:]`, the state from the last read. `main` uses `alarms_json[1:]`, the request. Tested on both branches:
   - `main`, no prior read: all four secondary alarms are written.
   - `fb-100w`, no prior read: only the header `0x16` is sent, so alarms 2 to 5 are not written.
   - `fb-100w`, after a read: the previously read alarms are written instead of the requested ones.

   Fix: restore `alarms_json[1:]` and the `main` comment. With that fix, snooze alarm 5 encodes as `0x50`.

2. **No way to choose snooze or one-time for alarm 5 from a caller.** The branch applies alarm 5 mode from the message only. If Prayer alarms need one-time, add a `snooze_alarm5` parameter (default `True`) to `set_alarms` in `gshock_api.py`, `watch_protocol.py`, and `standard_protocol.py`. This is not on the branch yet.

3. **Default behavior changes for alarm 5.** Any caller that doesn't pass a flag now gets snooze written on alarm 5 whenever it is enabled. This is intended by the branch, but it is a behavior change from `main`.

4. **Unverified bit positions and Sunday weekday.** Confirm `0x10`, `0x20`, and the Sunday weekday value against captures from the official app.

5. **Exercise read response.** Confirm the watch's reply to a `0x2D` read.

6. **Whitespace noise.** `time_io.py` has trailing-space removal, and `step_counter_io.py` has blank-line additions. Remove these to keep the diff focused.

## Test status

- The branch's `tests/` directory is not changed on this branch, so no new tests are added.
- The alarm encoder was checked on both branches by calling `AlarmsIOFunctional.prepare_watch_commands_set` directly. The result for alarms 2 to 5 shows the regression in issue 1.
- The weekday encoding and exercise codec were checked against the repo's captures.
- The existing test suite was not run against this branch.
