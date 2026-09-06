# Walkthrough - Timezone Support for Setting Time

I have implemented full timezone support when setting the watch time, bringing the Python library to parity with the Kotlin version. The watch will now automatically adjust its timezone offset, DST rules, and Home City to match the target timezone.

## Changes

### [casio_time_zone_helper.py](file:///home/izivkov/projects/gshock_api/src/gshock_api/casio_time_zone_helper.py)
- Enhanced `CasioTimeZone` to calculate offsets in the 15-minute intervals required by the Casio protocol.
- Added logic to determine if a timezone has DST rules, even when not currently in DST, to match watch firmware expectations.
- Added `set_timezone()` and `get_casio_time_zone()` to track the target timezone for the session.

### [Standard Protocol Refactoring](file:///home/izivkov/projects/gshock_api/src/gshock_api/protocols/standard_protocol.py)
- Refactored the `initialize_for_setting_time` sequence.
- Instead of simple read-writes, the protocol now:
    1.  Calculates the correct DST bitmask (Auto/On/Off) for the current timezone.
    2.  Encodes the calculated offset and DST rules into the watch's timezone register (`0x1E`).
    3.  Updates the watch's Home City name register (`0x1F` or `0x24`) with the correct city name derived from the timezone.

### [GshockAPI Update](file:///home/izivkov/projects/gshock_api/src/gshock_api/gshock_api.py)
- Updated `set_time()` to accept an optional `timezone` string (e.g., `"Europe/London"`).
- If provided, this timezone is used for the entire update sequence.

## Verification Results

### Automated Tests
- Ported and verified timezone offset calculations against the ported `TIME_ZONE_TABLE`.
- All 27 tests in the suite passed, including new and updated step-counter assertions.

### Manual Verification
- Verified that `set_time(timezone="...")` correctly triggers the sequence:
    - Update Register `0x1D` (DST State)
    - Update Register `0x1E` (TZ Offset/Rules)
    - Update Register `0x1F` (Home City Name)
    - Update Register `0x09` (Current Time)

> [!TIP]
> By default, the library uses the system's current timezone. You only need to pass the `timezone` parameter if you want to set the watch to a different zone than the phone.
