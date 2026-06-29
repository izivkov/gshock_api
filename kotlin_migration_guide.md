# Python to Kotlin Porting Guide: MTG-B1000 and GW-BX5600

This document outlines the architectural and logic changes introduced in the Python library to support the **MTG-B1000** and **GW-BX5600** G-Shock watches. Use this guide to update the Kotlin (`GShockAPI`) version.

## 1. MTG-B1000 (Second Dial & Home Time)

The MTG-B1000 features a secondary dial for a second time zone and differs in its handling of World Cities and time synchronization initialization.

### Files Modified & Required Changes

*   **`WatchInfo` / `WatchModel`**
    *   **Change:** Added `WatchModel.MTG`.
    *   **Change:** Added a new property `hasSecondDial` (default `false`).
    *   **Change:** Set MTG configuration: `hasSecondDial = true` and `hasWorldCities = false` (MTG skips `0x1F`).
*   **`CasioConstants`**
    *   **Change:** Added `CASIO_HOME_TIME = 0x24` characteristic constant for reading dual time zone data.
*   **`GshockAPI` (Main API class)**
    *   **Change:** Added `get_home_time(slot: int = 0)` function. Slot 0 returns the main (home) city data, and slot 1 returns the secondary city data used by the second dial.
    *   **Change:** In the initialization sequence (`initialize_for_setting_time` equivalent), added a conditional pass for watches with a secondary dial.
        ```python
        if watch_info.hasSecondDial:
            # Sync the second dial city after the main time is set.
            await SecondDialIO.write_reset_sequence(connection, slot=0)
            await SecondDialIO.request(connection)
        ```
    *   **Change:** Added a specific reset sequence command (`_write_reset_sequence(slot: int)`):
        *   Sends a command to `HANDLE_ALL_FEATURES_WRITE` (`0x000E` / `14`).
        *   Payload for Slot 0 (main time): `[0x21, 0x00, 0x01]`
        *   Payload for Slot 1 (second dial): `[0x21, 0x01, 0x01]`
*   **`HomeTimeIO` (New IO Module)**
    *   **Change:** Implements the request/response flow for the `0x24` characteristic.
*   **`MessageDispatcher`**
    *   **Change:** Route `"GET_HOME_TIME"` action to `HomeTimeIO.send_to_watch`.
    *   **Change:** Route characteristic `CASIO_HOME_TIME` (`0x24`) to `HomeTimeIO.on_received`.

---

## 2. GW-BX5600 (New Time Protocol)

The GW-BX5600 uses a different, dynamic time-sync protocol that handles payloads over standard SP_DATA notifications.

### Files Modified & Required Changes

*   **`WatchInfo`**
    *   **Change:** Set `hasNewTimeProtocol = true` for the `GW` (GW-BX5600) model.
*   **`CasioConstants`**
    *   **Change:** Added SP_DATA header notification bytes:
        *   `GW_BX5600_SP_DATA_HEADER_03 = 0x03`
        *   `GW_BX5600_SP_DATA_HEADER_05 = 0x05`
        *   `GW_BX5600_SP_DATA_HEADER_06 = 0x06`
*   **`MessageDispatcher`**
    *   **Change:** Route the three specific SP_DATA headers (`0x03`, `0x05`, `0x06`) to the new `GwBx5600TimeIO.on_received` handler.
*   **`GwBx5600TimeIO` (New IO Module)**
    *   **Change:** A new dedicated IO module created to handle the specific read-modify-write workflow for setting the time on the GW-BX5600 watch dynamically (using request steps and payload construction).
*   **`Connection`**
    *   **Change:** Removed hardcoded testing UUIDs from the `init_characteristics_map()` function, falling back strictly to querying the watch for supported characteristics (e.g., dynamically handling `HANDLE_CONFIG_NOTIFY`, `HANDLE_CONFIG_WRITE`, and `HANDLE_ALL_FEATURES_WRITE`).
*   **`time_adjustement_io.py`**
    *   **Change:** This file was completely removed. Time adjustment logic is now routed through the more standard `TimeIO` and `GwBx5600TimeIO`.

---

## Summary of Actionable Steps for Kotlin (`GShockAPI`)

1.  **Add `MTG`** to your `WatchModel` enums.
2.  **Add `hasSecondDial`** to your watch features/capabilities map. Set it to `true` for `MTG`, and disable `hasWorldCities` for `MTG`.
3.  **Implement `HomeTimeIO`** to fetch `0x24` by slot.
4.  **Implement `SecondDialIO`** (or a similar mechanism) to send the `0x21` reset sequence bytes when initializing time for watches where `hasSecondDial == true`.
5.  **Add `CASIO_HOME_TIME`** and the `GW_BX5600_SP_DATA_HEADER_*` bytes to your Kotlin constants.
6.  **Add routing** in the Kotlin `MessageDispatcher` to forward `0x03, 0x05, 0x06` headers to the `GwBx5600` specific handlers, and `0x24` to the Home Time handlers.
7.  **Ensure Characteristic Mapping** dynamically queries the connected watch rather than blindly mapping hardcoded UUIDs.
