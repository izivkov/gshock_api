# G-Shock API Release Notes

## [Unreleased] - GW-BX5600 Support & Protocol Updates

### Added
- **Full Support for GW-BX5600 Series Watches**: Added native capability and model mappings for the GW-BX5600 and GMW-BZ5000 watch lines.
- **SP Bulk Data Protocol (`0x17` / `0x19`)**: Implemented the Casio "SP_REQUEST" and "SP_DATA" bulk data transfer protocol required by the new BX watches to sync time and configure settings.
- **Dynamic Watch Capabilities**: Added a robust `hasNewTimeFormat` feature flag to `WatchInfo` that safely dictates whether a watch uses the legacy `ALL_FEATURES` sequential read/write or the new bulk `SP_DATA` protocol.

### Changed
- **Connection Type Safety**: Hardened `connection.write()` to safely handle both legacy hex-string payloads (`str`) and direct raw `bytearray`/`bytes` payloads natively, preventing type-cast exceptions during complex byte manipulation.
- **Dynamic Payload Construction**: SP Requests dynamically adjust their chunk sizes and request queries based on the watch's specific `worldCitiesCount` and `dstCount`, preventing buffer truncation or out-of-bounds exceptions on watches with different feature sets.
- **API Flow Consistency**: Integrated the BX time-setting logic directly into the standard `GshockAPI.set_time(current_time, offset)` flow. Consumer apps require zero logic changes to support the new watches.

### Fixed
- Fixed an issue where the `WatchInfo.reset()` method failed to clear dynamic feature flags upon disconnection, which could cause protocol corruption if a user connected a BX watch followed immediately by an older DW watch.
- Fixed an architectural signature mismatch where alternative timestamps and timezones passed to `set_time(current_time=..., offset=...)` were silently ignored by the new protocol in favor of the system clock.
