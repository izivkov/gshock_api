# G-Shock Health Data Protocol Analysis (DW-H5600)

This document outlines the reverse-engineered Bluetooth Low Energy (BLE) protocol used by the G-Shock DW-H5600 for transmitting health data (steps, calories, distance).

## Bluetooth Characteristics

- **Data Characteristic:** `CASIO_HEALTH_DATA` (0x05)
- **Control Characteristic:** `CASIO_SETTING_FOR_BLE` (0x11) / `0x10`
- **Encryption:** All health data payloads are XOR-encoded with the key `0xFF`.

## Data Formats

There are two primary data formats transmitted by the watch.

### 1. Live Update (Signature `000f`)
This is a snapshot of the current day's data up to the current time.

*   **Triggered by:** Sending `002E0014000000` to the control characteristic.
*   **Format:**
    *   **Byte [0:1]:** Signature `0x00 0x0f`
    *   **Byte [5]:** Year, encoded as a direct hex value representing the year from 2000 (e.g., `0x1a` = 26 → 2026).
    *   **Byte [6]:** Month (1-12)
    *   **Byte [7]:** Day (1-31)
    *   **Byte [8]:** Hour (0-23)
    *   **Byte [9]:** Minute (0-59)
    *   **Byte [15:16]:** **Steps** (16-bit Little-Endian)
    *   **Byte [18:19]:** **Calories** (16-bit Little-Endian). This is the direct kcal value.

### 2. Historical Day Summary (Signature `XX72`)
This contains the full-day summary for past days.

*   **Triggered by:** Sending `002E{index}72000000` where `{index}` is typically `64`, `63`, `62`, `61`, or `60`.
*   **Format:**
    *   **Byte [0:1]:** Signature (e.g., `0x63 0x72`). The first byte is the index.
    *   **Byte [5]:** Year (hex code, `0x26` = 2026)
    *   **Byte [6]:** Month (1-12)
    *   **Byte [7]:** Day (1-31). **Important:** This header date is one day *after* the actual data date. For example, if the header says Jan 7th, the data belongs to Jan 6th.
    *   **Byte [11:12]:** **Calories** (16-bit Little-Endian). **Important:** This value is halved. You must multiply by 2 to get the actual kcal.
    *   **Byte [15:16]:** **Steps** (16-bit Little-Endian)
    *   **Byte [19:20]:** **Distance** (16-bit Little-Endian). Stored in decimeters. Divide by 10 to get meters.

## Communication Flow

To fetch all health data, the API performs the following sequence:
1.  Initialize by writing `002EFFFFFFFFFF` to `0x11`
2.  Request Live data by writing `002E0014000000` to `0x11`
3.  For each historical index (`64`, `63`, `62`, `61`, `60`):
    *   Request history by writing `002E{index}72000000`
    *   Acknowledge by writing `070000000000000000000000000000` to `0x14`
    *   Wait a few seconds for the watch to transmit the data.

## Implementation Reference
The parsing logic is implemented in `src/gshock_api/iolib/health_data_io.py`. Testing and verification scripts can be found in `src/tests/` (e.g., `health_hardcoded_test.py`).
