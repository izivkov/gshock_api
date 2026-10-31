# fb-100w vs main (current)

Status: `fb-100w` has been merged into `main`.
- `origin/fb-100w`: `5f81d12`
- `origin/main`: `3aeb753`
- `fb-100w` is an ancestor of `main`.

The code on `main` is identical to `fb-100w`. The only difference is `docs/Expand F-B100W protocol support (#20).md`, which `main` adds. That doc still describes the pre-fix state and should be replaced with this summary.

## What the merged code does

### Exercise profile

- `ExerciseProfile` (`model/exercise_profile.py`): `step_goal` (default 10000), `height`, `weight`.
- `ExerciseIO` (`iolib/exercise_io.py`): encode and decode for opcode `0x2D`, plus request and write handling.
- Wire format, validated against captures:
  ```
  2D 00 GG GG GG GG HH HH WW WW
  GG = step goal, packed BCD, low digit pair first
  HH = height, packed BCD, each byte bit-inverted
  WW = weight, packed BCD, each byte bit-inverted
  ```
- Public API on `GshockAPI`: `get_exercise_profile()` and `set_exercise_profile(profile)`. These go through `WatchProtocol`, with implementations in `StandardProtocol`, so the Analogue and MIP protocols inherit them.
- Feature flag: `hasExcersiseProfile`, `True` for `ABL_100` and `F_B100`. The name contains a typo, so renaming it later is a breaking change.
- Not verified: the watch's read response. The captures contain only writes, so the `2D 00` response prefix is an assumption.

### Weekday encoding

- `dt.weekday()` (Mon = 0) became `dt.isoweekday()` (Mon = 1, Sun = 7) in `time_io.py`.
- Verified against 19 captured `SET_TIME` payloads from BX2, BX3, ABL, and DW-H5600. All 19 match `isoweekday()`.
- Not verified: Sunday = 7, since no capture is dated on a Sunday.

### Alarms

- Flag masks: `ONE_TIME_MASK = 0x20`, `SNOOZE_MASK = 0x10`. Existing: `ENABLED = 0x40`, `HOURLY_CHIME = 0x80`.
- Flags are written only when an alarm is enabled. One-time takes precedence over snooze.
- Decoded alarm JSON includes `oneTime` and `snooze` keys, both `false` unless the bits are set.
- Not verified: neither mask appears in any capture.
- Secondary alarms (2 to 5) are encoded from the request. The earlier regression, which used the last-read state, is fixed.
- `set_alarms(alarms, snooze_alarm5=True)` is on `GshockAPI`, `WatchProtocol`, and `StandardProtocol`. Alarm 5 (index 4) becomes a snooze alarm when the flag is `True`, or a one-time alarm when `False`. Other alarms are not changed. The method copies the list, so the caller's list is not modified.
- Tested on `main`: `set_alarms` with the default writes alarm 5 as `0x50`. With `snooze_alarm5=False` it writes `0x60`. Alarms 2 to 5 are written from the request.
- Default behavior change: any caller that doesn't pass the flag gets snooze on alarm 5 whenever it's enabled.

### Other

- `iolib/step_counter_io.py`: blank lines only.
- `src/examples/api_tests.py`: `test_exercise_profile`, which runs when the model has the flag.

## Issues on main that need fixing

1. **MTG-B3000 `SET_ALARMS` raises `AttributeError`.** `iolib/alarms_io.py` `send_to_watch_set` calls `AlarmsIOFunctional.prepare_watch_commands_set_mtg_b3000(message)` for `MTG_B3000`. Commit `b3acb9b` removed that method from `AlarmsIOFunctional`. `tests/test_code.py` `test_mtg_b3000_alarms_commands` fails for the same reason. The fix is to restore the method. It was on `029d440` and reads only the first alarm:

   ```python
       @staticmethod
       def prepare_watch_commands_set_mtg_b3000(message_json: str) -> list[BLEAction]:
           parsed: dict[str, object] = json.loads(message_json)
           alarms_json_arr: list[dict[str, object]] = parsed.get("value", [])  # type: ignore

           alarm_casio0 = alarms_inst_typed.from_json_alarm_first_alarm(alarms_json_arr[0])

           return [
               Write(handle=0x000E, data=bytes(alarm_casio0))
           ]
   ```

   Place it after `prepare_watch_commands_set`, inside `AlarmsIOFunctional`.

2. **`test_deterministic_time_encoding` is stale.** It still expects `5` for the weekday byte, from the old `weekday()` encoding. The test date, 2026-05-30, is a Saturday, so the correct value is `6` under `isoweekday()`. Change `self.assertEqual(encoded[7], 5)` to `6`, with a comment.

3. **Test count.** `main` runs 27 tests with 2 failing. The PR #20 head had 33 tests, including the `TestFb100w` class, which is not on `main`. If the PR #20 tests are wanted, merge them in, and move the `unittest.main()` guard to the end of the file.

4. **Unverified bit positions and Sunday weekday.** Confirm `0x10`, `0x20`, and the Sunday byte against captures from the official app.

5. **Exercise read response.** Confirm the watch's reply to a `0x2D` read.

## Test status on main

- `python -m unittest tests.test_code`: 27 tests run, 1 error (MTG-B3000 alarm set, issue 1) and 1 failure (weekday, issue 2).
- Direct check of `set_alarms` and the alarm encoder on `main`: alarms 2 to 5 are encoded correctly, and alarm 5 gets `0x50` by default and `0x60` with `snooze_alarm5=False`.