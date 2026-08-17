# G-Shock API Release Notes

## [2.0.39] - 2026-08-17 - WatchProtocol Design Pattern, WatchInfo Alignment, GW-BX5600 & ABL-100 Support

### Added
- **`WatchProtocol` Design Pattern**: Introduced abstract `WatchProtocol` interface and concrete implementations (`StandardProtocol`, `MipProtocol`, `AnalogueProtocol`) to decouple watch-specific behavior and reduce conditional branching.
- **`WatchInfo` Alignment with Kotlin `GShockAPI`**:
  - Aligned `WatchModel` enum with Kotlin (`GA`, `GW`, `DW_B5600`, `DW`, `GMW`, `GPR`, `GST`, `MSG`, `GB001`, `GBD`, `GBD_800`, `MRG_B5000`, `GCW_B5000`, `EQB`, `ECB`, `ABL_100`, `DW_H5600`, `GMW_BZ5000`, `GW_BX5600`, `MTG_B1000`, `MTG_B3000`, `GENERIC`).
  - Added `ModelInfo` dataclass containing 35+ per-model capability attributes matching Kotlin `WatchInfo.kt`.
  - Implemented exact official Casio model lookup table (`EXACT_MODEL_MAP`) supporting over 100 watch models mapped to exact model categories.
  - Added `WatchInfo.lookup_watch_info()` for scanned watch lookup and `alwaysConnected` filtering.
- **GW-BX5600 Watch Support & `CasioTimeZoneHelper`**:
  - Implemented `CasioTimeZoneHelper` with double-precision latitude/longitude coordinate lookups for world cities.
  - Updated `GwBx5600TimeIO` to construct the exact **94-byte write-back payload** for Step 2 (`0x03` → `0x06`) containing three 22-byte city location records matching the official Casio BLE app.
- **ABL-100 Step Counter Support**:
  - Created `StepCounterData` model (day of week, month, day of month, 144 hourly slots, 14 daily history slots, current day steps).
  - Updated `StepCounterIO` with multi-packet fragment accumulation, DRSP length announcement processing (`0x00`), end-transaction command sending (`0x04, 0x11, 0x00, 0x00, 0x00`), and structured payload parsing via `StepCounterIOFunctional`.

### Changed
- **`MessageDispatcher` Routing**: Updated `MessageDispatcher.on_received()` to use `WatchProtocol.extract_key()` and `WatchProtocol.unwrap_payload()`.
- **`GshockAPI` Method Delegation**: `GshockAPI` methods (`set_time`, `get_home_time`, `get_timer`, `set_timer`, `get_alarms`, `set_alarms`, `get_settings`, `set_settings`, `get_watch_condition`, `get_time_adjustment`) now delegate execution directly through `watch_info.protocol`.

### Fixed
- Fixed infinite recursion loop in `StandardProtocol.get_time_adjustment()` and `get_basic_settings()`.
- Fixed missing `lookup_watch_info()` attribute on `WatchInfo` that caused `BLE scan error` warnings during scanner connection filtering.

### Files Modified / Created
- `src/gshock_api/protocols/watch_protocol.py` - **New file** - Base `WatchProtocol` interface
- `src/gshock_api/protocols/standard_protocol.py` - **New file** - `StandardProtocol` implementation
- `src/gshock_api/protocols/mip_protocol.py` - **New file** - `MipProtocol` implementation
- `src/gshock_api/protocols/analogue_protocol.py` - **New file** - `AnalogueProtocol` implementation
- `src/gshock_api/protocols/__init__.py` - **New file** - Protocols package exports
- `src/gshock_api/casio_time_zone_helper.py` - **New file** - Casio timezone & coordinate helper
- `src/gshock_api/step_counter_data.py` - **New file** - Structured step counter record dataclass
- `src/gshock_api/watch_info.py` - Updated `WatchModel`, `ModelInfo`, exact model lookup table, and protocol integration
- `src/gshock_api/iolib/gw_bx5600_time_io.py` - Updated Step 2 payload construction to 94-byte city location records
- `src/gshock_api/iolib/step_counter_io.py` - Updated multi-packet accumulation, DRSP end-transaction, and structured parsing
- `src/gshock_api/message_dispatcher.py` - Updated to delegate key extraction and unwrapping to `WatchProtocol`
- `src/gshock_api/gshock_api.py` - Updated methods to delegate through `watch_info.protocol`
- `tests/test_code.py` - Expanded test suite to 24 unit tests covering protocols, model resolution, coordinates, and step counter
