# Implementation Plan - Refactor GShockAPI and WatchProtocol

Refactor the Python `gshock_api` library to align with the Kotlin version. The goal is to move implementation details from `GshockAPI` into `WatchProtocol` (specifically `StandardProtocol`), ensuring that all `iolib` interactions go through the protocol interface and removing circular dependencies where the protocol calls back into the API.

## User Review Required

> [!IMPORTANT]
> This refactoring will change the internal call flow of the library. While the high-level `GshockAPI` methods will remain the same for the user, the way they are implemented internally will change significantly to follow the `user -> GshockAPI -> Protocol -> IOLib` pattern.

## Proposed Changes

### [gshock_api]

#### [MODIFY] [watch_protocol.py](file:///home/izivkov/projects/gshock_api/src/gshock_api/protocols/watch_protocol.py)
- Update all method signatures to take `connection: Connection` instead of `api_inst: Any`.
- Add missing `iolib`-related methods to the `WatchProtocol` abstract class:
    - `get_watch_name`
    - `get_pressed_button`
    - `get_world_cities`
    - `get_dst_for_world_cities`
    - `get_dst_watch_state`
    - `get_app_info`
    - `get_step_count`
    - `get_step_counter_data`
    - `get_event_from_watch`
    - `set_reminders`
    - `get_watch_condition`
    - `get_app_info`
    - `get_time_adjustment`
    - `set_time_adjustment`

#### [MODIFY] [standard_protocol.py](file:///home/izivkov/projects/gshock_api/src/gshock_api/protocols/standard_protocol.py)
- Update signatures to take `connection`.
- Implement all methods by calling `message_dispatcher` or `iolib` classes directly.
- Move `initialize_for_setting_time` and other `read_write_*` helper logic from `GshockAPI` into `StandardProtocol` or `TimeIO`.
- Remove all references to `api_inst`.

#### [MODIFY] [analogue_protocol.py](file:///home/izivkov/projects/gshock_api/src/gshock_api/protocols/analogue_protocol.py)
- Update signatures to take `connection`.
- Update implementation to avoid calling back into `api_inst`.

#### [MODIFY] [mip_protocol.py](file:///home/izivkov/projects/gshock_api/src/gshock_api/protocols/mip_protocol.py)
- Update signatures to take `connection`.
- Update implementation to avoid calling back into `api_inst`.

#### [MODIFY] [gshock_api.py](file:///home/izivkov/projects/gshock_api/src/gshock_api/gshock_api.py)
- Remove `_method` implementations (e.g., `_get_timer`, `_get_alarms`).
- Update all public methods to delegate to `watch_info.protocol.method(self.connection)`.
- Remove internal helper methods like `initialize_for_setting_time`, `read_write_*`, and `read_and_write` as they will be handled by the protocol.

## Verification Plan

### Automated Tests
- Run existing tests to ensure no regressions in public API behavior.
- Add/update unit tests for `StandardProtocol` if they exist.

### Manual Verification
- Verify that the call flow matches the intended design: `user -> gshock_api -> protocol -> iolib`.
- Check that there are no circular dependencies between `GshockAPI` and the protocols.
