# Implementation Plan - Timezone Support for Setting Time

Align the Python `gshock_api` library with the Kotlin version by adding full timezone support when setting the watch time. This includes calculating and setting the correct timezone offset, DST rules, and world city information on the watch.

## User Review Required

> [!IMPORTANT]
> Setting the time will now automatically attempt to set the watch's timezone and DST rules to match the phone's (or a specified) timezone. This involves several writes to different watch registers (0x1D, 0x1E, 0x1F or 0x24) before the actual time is set.

## Proposed Changes

### [gshock_api]

#### [MODIFY] [casio_time_zone_helper.py](file:///home/izivkov/projects/gshock_api/src/gshock_api/casio_time_zone_helper.py)
- Update `CasioTimeZone` data class:
    - Add `offset` and `dst_offset` properties calculated in 15-minute intervals.
    - Implement logic to determine DST duration and rules matching the Kotlin implementation.
- Update `CasioTimeZoneHelper` class:
    - Add `set_timezone(timezone_name: str)` to track the desired timezone.
    - Add `get_casio_time_zone() -> CasioTimeZone` to retrieve the current setting.
    - Implement `is_equivalent(tz1, tz2)` for robust timezone matching.

#### [MODIFY] [dst_watch_state_io.py](file:///home/izivkov/projects/gshock_api/src/gshock_api/iolib/dst_watch_state_io.py)
- Add `set_dst(original_data: bytes, dst_value: int) -> bytes` to modify the DST bitmask for the main clock.

#### [MODIFY] [dst_for_world_cities_io.py](file:///home/izivkov/projects/gshock_api/src/gshock_api/iolib/dst_for_world_cities_io.py)
- Add `set_dst(original_data: bytes, casio_tz: CasioTimeZone) -> bytes` to encode timezone offset and DST rules into the 0x1E register format.

#### [MODIFY] [world_cities_io.py](file:///home/izivkov/projects/gshock_api/src/gshock_api/iolib/world_cities_io.py)
- Add `parse_city(time_zone_name: str) -> str` and `encode_and_pad(city_name: str, city_number: int) -> bytes` to prepare the 0x1F register data.

#### [MODIFY] [standard_protocol.py](file:///home/izivkov/projects/gshock_api/src/gshock_api/protocols/standard_protocol.py)
- Refactor `initialize_for_setting_time` and its helper methods:
    - Instead of just echoing back read values, apply the current `CasioTimeZone` settings using the new `set_dst` and `encode` methods before writing.
    - Support setting the main clock (index 0) with the target timezone while keeping other slots as-is.

#### [MODIFY] [gshock_api.py](file:///home/izivkov/projects/gshock_api/src/gshock_api/gshock_api.py)
- Update `set_time` signature to include an optional `timezone` parameter.

## Verification Plan

### Automated Tests
- Run existing tests to ensure no regressions.
- Add unit tests for the new `CasioTimeZone` calculation logic to verify offset and DST rule encoding.

### Manual Verification
- Test `set_time()` with and without a specified timezone.
- Verify (via logs or watch display if possible) that the timezone and DST state on the watch are updated correctly.
