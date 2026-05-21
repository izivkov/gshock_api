#!/usr/bin/env python3
"""
Hardcoded test for G-Shock health data decoding.
Verifies decode logic against known expected values from Casio app screenshots.

Expected values:
  Jan 7 (Live):    Steps=0,    Cal=702
  Jan 6 (History): Steps=1268, Cal=1780, Dist=800m
"""
import logging
import os
import sys

# Add src to path so we can import gshock_api
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gshock_api.logger import logger
from gshock_api.health_data import HealthData, DailyHealthData

def xor_decode(data: bytes, key: int = 255) -> bytes:
    return bytes([b ^ key for b in data])


def decode_health_data(decoded: bytes) -> DailyHealthData | None:
    """
    Decodes G-Shock health data buffers.
    
    Two known formats (after XOR decode):
    
    Live Update (signature 0x00 0x0F):
        [5]     Year (hex, e.g. 0x1a = 26 -> 2026)
        [6]     Month, [7] Day, [8] Hour, [9] Minute
        [15:17] Steps (16-bit LE)
        [18:20] Calories (16-bit LE, direct kcal)
    
    Historical Day Summary (signature byte[1]=0x72):
        [5] Year (0x26 = 2026), [6] Month, [7] Day (actual = day-1)
        [11:13] Calories/2 (16-bit LE, multiply by 2)
        [15:17] Steps (16-bit LE)
        [19:21] Distance in decimeters (÷10 for meters)
    """
    try:
        if len(decoded) < 16:
            return None

        msg_type = decoded[1]

        if msg_type == 0x0F:
            # --- Live Update ---
            from datetime import datetime
            year = 2000 + decoded[5]
            month = decoded[6]
            day = decoded[7]
            hour = decoded[8] if decoded[8] < 24 else 0
            minute = decoded[9] if decoded[9] < 60 else 0
            
            if not (1 <= month <= 12 and 1 <= day <= 31):
                return None
            
            steps = int.from_bytes(decoded[15:17], 'little')
            calories = int.from_bytes(decoded[18:20], 'little')
            
            dt = datetime(year, month, day, hour, minute)
            snapshot = HealthData(
                timestamp=int(dt.timestamp()),
                steps=steps,
                calories=calories,
            )
            
            return DailyHealthData(
                date=dt.strftime("%Y-%m-%d"),
                snapshots=[snapshot]
            )

        elif msg_type == 0x72:
            # --- Historical Day Summary ---
            from datetime import datetime, timedelta
            
            y_raw = decoded[5]
            year = 2026 if y_raw == 0x26 else (2025 if y_raw == 0x25 else 2000 + y_raw)
            month = decoded[6]
            day = decoded[7]
            
            if not (1 <= month <= 12 and 1 <= day <= 31):
                return None
            
            # Header date is day+1 of actual data
            dt_header = datetime(year, month, day)
            dt_local = dt_header - timedelta(days=1)
                
            calories = int.from_bytes(decoded[11:13], 'little') * 2
            steps = int.from_bytes(decoded[15:17], 'little')
            distance = int.from_bytes(decoded[19:21], 'little') // 10 if len(decoded) >= 21 else 0
            
            snapshot = HealthData(
                timestamp=int(dt_local.timestamp()),
                steps=steps,
                calories=calories,
                distance=distance
            )
            
            return DailyHealthData(
                date=dt_local.strftime("%Y-%m-%d"),
                snapshots=[snapshot]
            )

        else:
            logger.warning(f"Unknown buffer format signature: {decoded[:2].hex()}")
            return None

    except Exception as e:
        logger.error(f"Error parsing health data: {e}")
        return None

def run_hardcoded_test():
    logger.info("Starting Health Data Decoding Test...")

    # Test buffers with expected values
    test_cases = [
        # (hex_buffer, expected_date, expected_steps, expected_calories, description)
        ("05FFF0FFFFFFE5FEF8F1DFC9BAFFFFFFFFFFFF41FDEF7B",
         "2026-01-07", 0, 702, "Jan 7 Live Update"),
        ("059C8DFFFFFFD9FEF813A2D185FCFFA30BFBFFFFBFE0FFFFF0FF9FFFFFFFFF9DFFFFFFFFF0F0FFFFD8FFFFFFFFFEC9EFDAFEFFEECF009E010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101FF00A157FFCFFFC8FF9B00007E2B",
         "2026-01-06", 1268, 1780, "Jan 6 History Record"),
    ]
    
    all_pass = True
    
    for hex_str, exp_date, exp_steps, exp_cal, desc in test_cases:
        data = bytearray.fromhex(hex_str)
        payload = data[1:]
        decoded = xor_decode(payload)
        
        daily = decode_health_data(decoded)
        
        if daily is None:
            print(f"  ✗ {desc}: Failed to decode")
            all_pass = False
            continue
        
        date_ok = daily.date == exp_date
        steps_ok = daily.total_steps == exp_steps
        cal_ok = daily.total_calories == exp_cal
        
        status = "✓" if (date_ok and steps_ok and cal_ok) else "✗"
        if not (date_ok and steps_ok and cal_ok):
            all_pass = False
        
        print(f"  {status} {desc}:")
        print(f"    Date:     {daily.date}  (expected: {exp_date})  {'✓' if date_ok else '✗'}")
        print(f"    Steps:    {daily.total_steps}  (expected: {exp_steps})  {'✓' if steps_ok else '✗'}")
        print(f"    Calories: {daily.total_calories}  (expected: {exp_cal})  {'✓' if cal_ok else '✗'}")
        print(f"    Distance: {daily.total_distance} m")
    
    print()
    if all_pass:
        print("ALL TESTS PASSED ✓")
    else:
        print("SOME TESTS FAILED ✗")
    
    return all_pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run_hardcoded_test()
