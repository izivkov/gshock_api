# Kotlin Migration Guide: GW-BX5600 & MTG-B1000 Support

This guide outlines the files and architectural changes needed to port the GW-BX5600 bulk-data time setting protocol and MTG-B1000 dual-dial support to the Kotlin version of the library.

## 1. `CasioConstants.kt`
You must add the new `SP_REQUEST` (0x17) and `SP_DATA` (0x19) handles, UUIDs, and response header keys.

**Additions:**
* `CASIO_SET_CONFIGURATION_CHARACTERISTIC_UUID` = "26eb002e-b012-49a8-b1f8-394fb2032b0f"
* `CASIO_GET_CONFIGURATION_CHARACTERISTIC_UUID` = "26eb002f-b012-49a8-b1f8-394fb2032b0f"
* `HANDLE_SP_REQUEST` = `0x17`
* `HANDLE_SP_DATA` = `0x19`
* Add to Characteristics map: `"GW_BX5600_SP_DATA_HEADER_03": 0x03`, `"GW_BX5600_SP_DATA_HEADER_05": 0x05`, `"GW_BX5600_SP_DATA_HEADER_06": 0x06`

## 2. `Connection.kt`
Configure the BLE GATT map to register the new characteristics and handle the write types.

**Modifications:**
* Map handle `0x17` to `CASIO_SET_CONFIGURATION_CHARACTERISTIC_UUID`.
* Map handle `0x19` to `CASIO_GET_CONFIGURATION_CHARACTERISTIC_UUID`.
* Ensure handle `0x17` is added to the `NO_RESPONSE_HANDLES` (or uses `BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE` in Android BLE).
* **Crucial:** Ensure the `write` function in Kotlin can accept raw `ByteArray` operations safely, as the old logic may have assumed String-to-Hex conversions exclusively (like Python's `to_casio_cmd`).

## 3. `WatchInfo.kt` / `WatchModel.kt`
Add the capability flags and model identification so the library knows when to use the new protocol.

**Modifications:**
* Add `GW_BX` to the `WatchModel` enum.
* In the `prefix_map` / resolution logic, add `"GW-BX"` mapping to `GW_BX`. **Note**: This must be checked *before* `"GW"` to prevent overlapping.
* Add `var hasNewTimeFormat: Boolean = false` to the model state properties.
* In the model overrides/capabilities map, set `hasNewTimeFormat = true` for the `GW_BX` model.
* Ensure that the `reset()` or `clear()` function explicitly sets `hasNewTimeFormat = false` so state doesn't leak between connections.

## 4. `MessageDispatcher.kt`
Wire up the incoming BLE notification fragments so they route to the new IO class.

**Modifications:**
* Map `0x03`, `0x05`, and `0x06` (from `CasioConstants`) to the `GwBx5600TimeIO.onReceived` method in the data dispatch table.

## 5. `GshockAPI.kt`
Update the high-level `setTime` facade to transparently route to the new protocol when the flag is present.

**Modifications:**
* Inside `setTime(timeMs: Long, offset: Int)`, add a conditional branch at the very beginning:
  ```kotlin
  if (watchInfo.hasNewTimeFormat) {
      MessageDispatcher.GwBx5600TimeIO.request(connection, timeMs, offset)
      return
  }
  ```
* Do not modify the legacy `initializeForSettingTime()` or `_setTime()` paths. 

## 6. Create `GwBx5600TimeIO.kt`
This is the only new file required. It must mirror the read-modify-write workflow using Kotlin Coroutines and the SP bulk protocol.

**Key Implementation Details:**
1. **The Entry Point:** `fun request(connection, timeMs, offset)` that delegates to a `setTime` coroutine.
2. **The Fragment Accumulator:** Create an `onReceived(data: ByteArray)` function that appends incoming BLE chunks to a local `ByteArray` accumulator. It must dynamically compute the expected size based on capabilities (e.g., `1 + (ceil(worldCitiesCount / 2) * 9)` for step 2) and resume the suspending coroutine once the expected length is reached.
3. **The Protocol Steps:**
   * **Step 1:** Construct `0x05` request dynamically (Appending `1D 00` and `24 XX`). Await response -> slice exactly `35` bytes -> mutate `byte[0] = 0x02` -> fill trailing indices `27..34` with `0xFF` -> `connection.write(0x19, bytes)`.
   * **Step 2:** Construct `0x03` request dynamically (Appending `ceil(worldCitiesCount/2)` copies of `1E 00`). Await response -> mutate `byte[0] = 0x06` -> write back.
   * **Step 3:** Construct `0x06` request dynamically (Loop `0` to `worldCitiesCount`, appending `1F` and the interleaved index `(i / 2) + if (i % 2 != 0) 6 else 0`). Await response -> write back unchanged.
   * **Step 4:** Construct the 11-byte `0x09` time command payload (same as legacy) and write it to the standard `ALL_FEATURES` handle (`0x0E`).

---

## MTG-B1000 Support - Dual Analogue Dial Protocol

The MTG-B1000 has two independent analogue dials: the main dial follows the standard G-Shock time protocol, while the second dial requires an additional sequence bracketed by ResetSequence commands after the main time is set.

### 1. `WatchModel.kt` (Enum Addition)
Add the MTG-B1000 model to the enum.

**Additions:**
* Add `MTG_B1000` to the `WatchModel` enum.

### 2. `WatchInfo.kt`
Add capability flags for second dial support.

**Modifications:**
* Add `var hasSecondDial: Boolean = false` to the model state properties.
* In the `prefix_map` / model resolution logic, add `"MTG-B1000"` mapping to `MTG_B1000`. **Important:** This mapping must be checked *before* generic prefixes like `"MTG"` to prevent overlapping.
* In the model overrides/capabilities map, add an entry for `MTG_B1000` with `hasSecondDial = true`:
  ```kotlin
  {
      model: WatchModel.MTG_B1000,
      worldCitiesCount: 6,
      hasReminders: true,
      shortLightDuration: "2s",
      longLightDuration: "4s",
      hasSecondDial: true
  }
  ```
* Ensure that the `reset()` or `clear()` function explicitly sets `hasSecondDial = false`.

### 3. `GshockAPI.kt`
Integrate the MTG-B1000 second dial sequence into the main `setTime` flow.

**Modifications:**
* At the end of the `setTime(timeMs: Long, offset: Int)` method, **after** the legacy `initializeForSettingTime()` and `_setTime()` calls complete, add:
  ```kotlin
  if (watchInfo.hasSecondDial) {
      MtgB1000TimeIO.setSecondDial(connection)
  }
  ```

### 4. Create `MtgB1000TimeIO.kt` (New File)
This new file implements the MTG-B1000 second dial sequence.

**Key Implementation Details:**
The protocol consists of ResetSequence commands bracketing a read-modify-write cycle:

1. **Entry Point:** `suspend fun setSecondDial(connection: ConnectionProtocol)` that orchestrates the full sequence.
2. **ResetSequence Constants:**
   - `RESET_SEQUENCE_START = byteArrayOf(0x21, 0x00, 0x01)` // dial 0
   - `RESET_SEQUENCE_END = byteArrayOf(0x21, 0x01, 0x01)` // dial 1
3. **The Protocol Steps:**
   - Send `RESET_SEQUENCE_START` via `connection.write(0x000E, ...)` (write-with-response handle).
   - Call `DstWatchStateIO.request(...)` to fetch current DST state (handle `0x1D`).
   - Write the DST state back via `connection.write(0x000E, ...)`.
   - Call `DstForWorldCitiesIO.request(city_number=0)` and `...request(city_number=1)` to fetch DST city data (handle `0x1E`).
   - Write both DST city entries back.
   - Call `WorldCitiesIO.request(city_number=0)` and `...request(city_number=1)` to fetch world city coordinates (handle `0x1F`).
   - Write both world city entries back.
   - Send `RESET_SEQUENCE_END` via `connection.write(0x000E, ...)`.

4. **Error Handling:** If any step times out or fails, log the error and propagate the exception; the watch's second dial may be out of sync, but the main time remains correct.

---

## Summary of Modified Files

| File | Change Type | Description |
|------|------------|-------------|
| `src/gshock_api/watch_info.py` | Modified | Added `MTG_B1000` model enum value and `hasSecondDial` capability flag |
| `src/gshock_api/gshock_api.py` | Modified | Integrated MTG-B1000 second dial sequence into `set_time()` flow |
| `src/gshock_api/iolib/mtg_b1000_time_io.py` | **New** | MTG-B1000 dual-dial time-setting protocol implementation |
