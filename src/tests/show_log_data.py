#!/usr/bin/env python3
import sys
import os
import re

# Add src to path so we can import gshock_api
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gshock_api.iolib.health_data_io import HealthDataIO

def parse_logs():
    log_file = os.path.join(os.path.dirname(__file__), "parsed.txt")
    
    # Regex to find lines like "Value: 05..."
    value_re = re.compile(r"Value:\s*(05[0-9a-fA-F]+)")
    
    records_found = []
    
    with open(log_file, "r") as f:
        for line in f:
            match = value_re.search(line)
            if match:
                hex_str = match.group(1)
                data = bytearray.fromhex(hex_str)
                payload = data[1:] # strip leading 05
                decoded = HealthDataIO.xor_decode(payload, key=255)
                
                daily_records = HealthDataIO.decode_health_data(decoded)
                if daily_records:
                    for record in daily_records:
                        records_found.append((hex_str[:20] + "...", record))

    if not records_found:
        print("No health data records could be decoded from the log.")
        return

    print("=" * 80)
    print("DECODED HEALTH DATA FROM LOGS")
    print("=" * 80)
    
    # Group by date for cleaner output
    records_by_date = {}
    for raw, rec in records_found:
        if rec.date not in records_by_date:
            records_by_date[rec.date] = []
        records_by_date[rec.date].append((raw, rec))
        
    for date in sorted(records_by_date.keys()):
        print(f"\nDate: {date}")
        print("-" * 40)
        for raw, rec in records_by_date[date]:
            snap = rec.snapshots[0]
            dist_str = f", Distance: {snap.distance} m" if hasattr(snap, "distance") and snap.distance > 0 else ""
            print(f"  [Raw: {raw}]")
            print(f"  -> Steps: {snap.steps}, Calories: {snap.calories} kcal{dist_str}")

if __name__ == "__main__":
    parse_logs()
