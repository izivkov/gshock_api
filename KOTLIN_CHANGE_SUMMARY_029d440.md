# Kotlin parity summary since commit 029d440ea5852e618c95e66dcdee82b4f1f03eb4

This document summarizes the Python project changes introduced after commit `029d440ea5852e618c95e66dcdee82b4f1f03eb4` and is intended to help update the corresponding Kotlin implementation of GShockAPI.

## Purpose and scope

The codebase has moved beyond the state captured by the original commit in a few important ways:

- F-B100W protocol support was merged and refined.
- Exercise-profile functionality was added as a first-class watch feature.
- Alarm handling became more model-aware and safer for watches with different alarm counts.
- Protocol and example code were cleaned up so the watch-specific behavior is more explicit and less brittle.

For a Kotlin port, the relevant work is not just about adding a new method: it is about matching the same capability flags, payload logic, and protocol routing used by the current Python library.

## High-level project changes

| Area | What changed in Python | Kotlin impact |
| --- | --- | --- |
| F-B100W / exercise profile support | Added exercise profile model, encode/decode IO, and public API methods | Kotlin must add equivalent model, IO parser, and high-level API methods |
| Alarm protocol correctness | Fixed alarm-slot selection based on `watch_info.alarmCount`; copy-on-write behavior added before mutation | Kotlin needs mode-aware final-slot logic and safe list copying |
| Watch-model capability handling | Official model capabilities and protocol checks were refined | Kotlin should keep capability flags aligned with the Python `WatchInfo` model |
| Protocol cleanup | Standard protocol methods delegate through watch-specific logic and use clearer model-aware flows | Kotlin should preserve the same delegation pattern |
| Example safety | API example now keeps destructive actions behind a flag | Kotlin samples should stay safe-by-default |

## 1) F-B100W support and exercise-profile addition

The most significant feature addition since the reference commit is support for the F-B100W exercise profile payload.

### Python changes

The following files were added or extended:

- `src/gshock_api/model/exercise_profile.py`
- `src/gshock_api/iolib/exercise_io.py`
- `src/gshock_api/gshock_api.py`
- `src/gshock_api/watch_info.py`
- `src/gshock_api/protocols/watch_protocol.py`
- `src/gshock_api/protocols/standard_protocol.py`

The public API now exposes:

- `GshockAPI.get_exercise_profile()`
- `GshockAPI.set_exercise_profile(profile)`

The exercise profile itself is represented as a model object and encoded/decoded in the I/O layer. The watch capability is also surfaced via model metadata, so unsupported watches do not blindly attempt the feature.

### Kotlin porting implications

The Kotlin library should add:

- `ExerciseProfile` model class or data class
- `ExerciseIo` request/encode/decode logic
- `GshockApi.getExerciseProfile()` and `setExerciseProfile()` methods
- model capability flags for the F-B100W / ABL-100 feature set
- protocol mapping so the watch can route exercise-profile requests through the correct protocol handler

This is a structural parity change, not only a convenience wrapper.

## 2) Alarm handling became model-aware and safer

After the reference commit, alarm handling was tightened in several ways.

### Python changes

Relevant files:

- `src/gshock_api/iolib/alarms_io.py`
- `src/gshock_api/model/alarms.py`
- `src/gshock_api/protocols/standard_protocol.py`
- `tests/test_alarms.py`

The main changes are:

- alarm payload generation is now more explicit and uses a flat alarm model instead of burying conversion logic in the model layer
- the final alarm slot is chosen based on `watch_info.alarmCount` rather than assuming a fixed fifth slot
- the input alarm list is copied before mutation so the caller's list is preserved
- snooze vs one-time alarm behavior is maintained correctly
- fixed behavior for MTG-B3000 single-alarm watches and correct handling of 1, 4, or 5 alarm slots

The test suite now includes checks for the last-alarm-slot logic and payload encoding.

### Kotlin porting implications

The Kotlin library should mirror these rules:

- keep alarm data model flat and explicit
- compute the effective last alarm index as `max(0, alarmCount - 1)`
- do not mutate the caller's alarm list in place
- set the last valid slot's `snooze` / `oneTime` flags according to the requested behavior
- preserve the legacy default behavior for snooze alarm 5 unless the caller explicitly overrides it
- handle MTG-B3000 and other watches with different alarm capacity without assuming a fixed slot layout

## 3) Protocol architecture and watch capability cleanup

The protocol flow after this commit is more model-driven and safer for mixed watch families.

### Python changes

Relevant files:

- `src/gshock_api/protocols/standard_protocol.py`
- `src/gshock_api/protocols/watch_protocol.py`
- `src/gshock_api/watch_info.py`
- `src/gshock_api/gshock_api.py`

Important behaviors:

- `GshockAPI` delegates calls through `watch_info.protocol`
- `StandardProtocol.set_time()` does the timezone preparation and then delegates the write path
- model-specific behavior is checked using role-capability flags instead of scattered assumptions
- the standard flow is clearer about read/write DST and world-city settings before time is written

### Kotlin porting implications

The Kotlin equivalent should keep:

- a watch-protocol abstraction similar to `WatchProtocol`
- model capability fields for features such as exercise profile, second dial, world-city configuration, DST support, and alarm layout
- a single high-level API entry point that delegates to the active protocol rather than hardcoding each watch behavior in one monolithic class

## 4) Example and test updates

The example and tests were cleaned up to be safer and more representative of the supported workflow.

### Python changes

Relevant files:

- `src/examples/api_tests.py`
- `tests/test_alarms.py`
- `RELEASE_NOTES.md`

Notable changes:

- destructive actions are gated behind a boolean flag
- the example sequence is safer for default runs
- alarm behavior is validated by unit tests rather than relying on manual watch-side verification alone
- release notes reflect the current merged state of the protocol work

### Kotlin porting implications

The Kotlin sample app should:

- avoid destructive watch writes unless explicitly enabled
- show read-only feature discovery early in the flow
- keep examples safe and reproducible for any user running the app on a real watch

## 5) Recommended Kotlin parity checklist

1. Add F-B100W exercise-profile support to the model and protocol layers.
2. Add watch-model capability flags that match the Python library semantics.
3. Implement model-aware alarm-slot selection using `alarmCount` and preserve existing call semantics.
4. Keep a copy-on-write step when writing alarm arrays.
5. Ensure time-setting and protocol routing still delegate through the active protocol abstraction.
6. Keep demo/test code safe by default and treat real watch writes as opt-in behavior.
7. Treat the release notes as the authoritative summary of current Python behavior.

## Files most relevant for Kotlin parity

- `src/gshock_api/gshock_api.py`
- `src/gshock_api/watch_info.py`
- `src/gshock_api/protocols/standard_protocol.py`
- `src/gshock_api/protocols/watch_protocol.py`
- `src/gshock_api/iolib/alarms_io.py`
- `src/gshock_api/model/alarms.py`
- `src/gshock_api/model/exercise_profile.py`
- `src/gshock_api/iolib/exercise_io.py`
- `src/examples/api_tests.py`
- `tests/test_alarms.py`
- `RELEASE_NOTES.md`

## Bottom line

The project has evolved since commit `029d440ea5852e618c95e66dcdee82b4f1f03eb4` in a direction that is both more capable and more deliberate:

- the library supports more watch features,
- protocol behavior is more model-aware,
- alarm and exercise-profile handling are now first-class features,
- and the Kotlin counterpart should update to match that current behavior rather than the earlier baseline.
