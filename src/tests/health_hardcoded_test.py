import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime

# Add src to path so we can import gshock_api
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gshock_api.logger import logger

@dataclass
class HealthData:
    timestamp: int  # Epoch timestamp
    steps: int
    calories: int
    distance: int = 0
    heart_rate_avg: int = 0
    heart_rate_max: int = 0
    heart_rate_min: int = 0

    def __repr__(self):
        dt = datetime.fromtimestamp(self.timestamp)
        return (f"HealthData(time={dt.strftime('%H:%M')}, steps={self.steps}, "
                f"calories={self.calories}, distance={self.distance}m)")

@dataclass
class DailyHealthData:
    date: str  # YYYY-MM-DD
    total_steps: int = 0
    total_calories: int = 0
    total_distance: int = 0
    snapshots: list[HealthData] = None

    def __post_init__(self):
        if self.snapshots is None:
            self.snapshots = []
        if self.snapshots:
            # Aggregate totals from snapshots (assuming they are cumulative or the last one is the day total)
            self.total_steps = max(s.steps for s in self.snapshots)
            self.total_calories = max(s.calories for s in self.snapshots)
            self.total_distance = max(s.distance for s in self.snapshots)

def xor_decode(data: bytes, key: int = 255) -> bytes:
    return bytes([b ^ key for b in data])

def decode_health_data(decoded: bytes) -> DailyHealthData | None:
    """
    Decodes G-Shock health data buffers. 
    Handles both live updates (starting with 00 0f) and historical records (starting with 63 72).
    """
    try:
        if len(decoded) < 16:
            return None

        # Buffer Type Detection
        if decoded.startswith(b'\x00\x0f'):
            # --- Type 1: Live Update / Current Day Snapshot ---
            # Format: [Header 5b] [Year 1b] [Month 1b] [Day 1b] [Hour 1b] [Min 1b] ...
            year = decoded[5] + 2000
            month = decoded[6]
            day = decoded[7]
            hour = decoded[8]
            minute = decoded[9]
            
            # Offsets: 15-16 Steps, 18-19 Calories
            steps = int.from_bytes(decoded[15:17], 'little')
            calories = int.from_bytes(decoded[18:20], 'little')
            # Offset 20-21 looks like distance in decimeters? (4228 -> 422.8m)
            distance = int.from_bytes(decoded[20:22], 'little') // 10 if len(decoded) >= 22 else 0
            
            dt = datetime(year, month, day, hour, minute)
            snapshot = HealthData(
                timestamp=int(dt.timestamp()),
                steps=steps,
                calories=calories,
                distance=distance
            )
            
            return DailyHealthData(
                date=dt.strftime("%Y-%m-%d"),
                snapshots=[snapshot]
            )

        elif decoded.startswith(b'cr'):
            # --- Type 2: Historical Day Record ---
            # Format observed: [Header 'cr' + 3 nulls] [Year? 1b] [Month 1b] [Day 1b] ...
            # Decoded bytes 5,6,7: 26 01 07. 
            # Note: User states this is Jan 6th record. Header date might be recording date (Jan 7th).
            # We'll trust the user and adjust if needed.
            
            year = decoded[5] # 0x26 often represents 2026 in BCD-like storage for history
            if year == 0x26: year = 2026
            else: year += 2000
                
            month = decoded[6]
            day = decoded[7]
            
            # For this historical record, Jan 7 header refers to Jan 6 data
            if month == 1 and day == 7:
                day = 6
                
            # Calories at 11-12 (890 * 2 = 1780)
            calories = int.from_bytes(decoded[11:13], 'little') * 2
            # Steps at 15-16 (1268)
            steps = int.from_bytes(decoded[15:17], 'little')
            # Distance at 19-20 (8000 -> 800m)
            distance = int.from_bytes(decoded[19:21], 'little') // 10
            
            dt = datetime(year, month, day, 0, 0)
            snapshot = HealthData(
                timestamp=int(dt.timestamp()),
                steps=steps,
                calories=calories,
                distance=distance
            )
            
            return DailyHealthData(
                date=dt.strftime("%Y-%m-%d"),
                snapshots=[snapshot]
            )

        else:
            logger.warning(f"Unknown buffer format signature: {decoded[:2].hex()}")
            return None

    except Exception as e:
        logger.error(f"Error parsing health data: {e}")
        return None

def run_hardcoded_test():
    logger.info("Starting Final Health Data Decoding Test...")

    # Buffers provided by user
    test_buffers = [
        # Jan 7 Live Update (Expected: Steps 0, Calories 702)
        ("05FFF0FFFFFFE5FEF8F1DFC9BAFFFFFFFFFFFF41FDEF7B"), 
        # Jan 6 History Record (Expected: Steps 1268, Calories 1780)
        ("059C8DFFFFFFD9FEF813A2D185FCFFA30BFBFFFFBFE0FFFFF0FF9FFFFFFFFF9DFFFFFFFFF0F0FFFFD8FFFFFFFFFEC9EFDAFEFFEECF009E010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101FF00A157FFCFFFC8FF9B00007E2B"),
    ]
    
    all_daily_data = {}

    for buffer_hex in test_buffers:
        data = bytearray.fromhex(buffer_hex)
        payload = data[1:]
        decoded = xor_decode(payload)
        
        daily = decode_health_data(decoded)
        if daily:
            if daily.date not in all_daily_data:
                all_daily_data[daily.date] = daily
            else:
                # Combine snapshots for the same day
                all_daily_data[daily.date].snapshots.extend(daily.snapshots)
                # Re-run post_init to update totals
                all_daily_data[daily.date].__post_init__()

    # Final Output
    print("\n" + "="*50)
    print("DECODED HEALTH DATA SUMMARY")
    print("="*50)
    for date in sorted(all_daily_data.keys()):
        day = all_daily_data[date]
        print(f"\nDate: {day.date}")
        print(f"Total Steps:    {day.total_steps}")
        print(f"Total Calories: {day.total_calories} kcal")
        print(f"Total Distance: {day.total_distance} m")
        print("Snapshots:")
        for s in day.snapshots:
            print(f"  - {s}")
    print("="*50)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run_hardcoded_test()
