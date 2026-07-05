# Release Notes

## Unreleased - step-counter branch

This branch introduces initial support for reading step-counter data from compatible watches and refines the example API test flow.

### Added
- Added step-counter support via a new step counter I/O handler and a new `GshockAPI.get_step_count()` API.
- Registered activity-record handling so the watch can dispatch step-count notifications correctly.
- Added a capability flag for watches that support step counting in the watch-info model.

### Updated
- Updated the example API test script to read the current step count and to make destructive test actions optional.
- Adjusted BLE connection and message-dispatch handling to support the new activity-record flow.

### Notes
- The current branch changes are based on the diff against `main` and are intended as a starting point for release documentation.
