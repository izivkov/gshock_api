# G-Shock API Release Notes

## [2.0.40] - 2026-09-02 - Step counter UX and example improvements

### Added
- `StepCounterData` friendly representations: `hourly_intervals`, `hourly_by_hour`, and `daily_history_list` are now populated by the IO parser for easier consumption by applications.
- Example CLI flags: `--permissive` (treat missing 10-minute slots as zero for aggregation) and `--raw` (print raw payload hex) added to `src/examples/step_counter.py` for debugging and flexible output.

### Changed
- Moved formatting/aggregation helpers into `StepCounterIOFunctional.parse()` so the IO layer produces ready-to-use, human-friendly fields. The model remains a plain data container with these friendly fields populated by the parser.
- Hourly aggregation is now strict by default: if any 10-minute slot in an hour is missing the whole hour is reported as `None`. Use `--permissive` to sum missing slots as zero.

### Notes
- The example `src/examples/step_counter.py` was updated to print the new fields and to include the new CLI flags for permissive aggregation and raw payload output.


## [2.0.41] - 2026-09-02 - Step counter timestamp parsing, robustness, and example refinements

### Added
- `GshockAPI.get_step_summary()` and `GshockAPI.get_step_history()` convenience methods to explicitly request a quick daily total or the full step history.
- Example improvements in `src/examples/step_counter.py`: `--summary`, `--history`, and `--strict` flags; improved stdin/HCI handling; and debug logging for matched HCI candidates.
- Example now estimates calories locally and displays an `estimated_calories_kcal` field in `src/examples/step_counter.py`. The example accepts `--weight` (default `70.0` kg) and `--stride` (default `0.762` m) to control the estimate.

### Fixed
- `StepCounterIOFunctional.parse()` now decodes the 6-byte packed-BCD timestamp correctly and tolerates sentinel bytes (0xFE/0xFF) for missing subfields. When year/month/day are present a `timestamp` (`datetime`) is constructed; otherwise the parser emits a warning and leaves `timestamp=None`.

### Changed
- `StepCounterData` now exposes a single `timestamp: datetime | None` field (replacing separate `day_of_week/month/day_of_month` header fields) so callers get a canonical instant covering year/month/day/hour/minute/second when available.
- IO-level parsing is more robust: the example now prefers the longest successfully-parsed HCI/STDIN candidate (to avoid picking short/truncated fragments), and warns when payloads are truncated or timestamp bytes are invalid.
- `src/examples/step_counter.py` strict mode (`--strict`) will dump the raw payload hex to `failed_step_payload_YYYYMMDD_HHMMSS.hex` and fail loudly when timestamp decoding is invalid — useful for deterministic CI or postmortem debugging.

### Notes
- The timestamp decoding change improves ergonomics for consumers by providing a single, validated `datetime`. The parser remains conservative: invalid or incomplete timestamp bytes produce warnings and do not crash normal (non-strict) workflows.
- If you rely on legacy `day_of_week/month/day_of_month` fields, update callers to use `timestamp` or access derived properties as needed.


## [2.0.42] - 2026-09-02 - Example UX, calorie estimates, and connection robustness

### Added
- Example `src/examples/step_counter.py` now computes a local calorie estimate and prints `estimated_calories_kcal`. The example accepts `--weight` and `--stride` (defaults: `70.0` kg, `0.762` m) to control the estimate.
- The example prints a tidy two-column `Summary` table and tabulated `Hourly by hour` and `Today (10-minute slots by hour)` views for easier human consumption.

### Fixed
- Prevented a fatal formatting error in the example summary output by using safe string padding when rendering fields.
- Improved BLE connection reliability: ensure GATT services are discovered after connect by invoking `BleakClient.get_services()` where available so characteristics and notifications are reliably found.
- `src/examples/api_tests.py` now checks the boolean return value of `Connection.connect(...)` and aborts early when service discovery or connect fails to avoid proceeding with an incomplete connection.

### Changed
- Example stdin/HCI parsing: prefer the longest successfully-parsed HCI/STDIN candidate to avoid selecting truncated fragments; skip parse-time errors and log matched candidate previews for easier debugging.
- `src/examples/step_counter.py` adds `--weight` and `--stride` CLI flags and displays allocated per-hour calories in the hourly table when an overall calories estimate is available.

### Notes
- These changes are purely UX and parser-level: the IO parser still populates friendly model fields (`hourly_intervals`, `hourly_by_hour`, `daily_history_list`) and the underlying data model remains backward compatible. The connection/service discovery change improves runtime robustness across Bleak backends and watch models.


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
