
import re
from datetime import datetime, timedelta

def xor_decode(data, key=255):
    return bytes([b ^ key for b in data])

def analyze_all_records(file_path):
    with open(file_path, 'r') as f:
        content = f.read()

    # Find all 05... notifications on handle 0x0013 and 0x0018
    notifies = re.findall(r'Notify Handle: 0x00[13|18]+ Value: (05[0-9A-F]+)', content)
    
    unique_days = {}

    for hex_str in notifies:
        data = bytes.fromhex(hex_str)
        if len(data) < 16:
            continue
            
        payload = data[1:]
        decoded = xor_decode(payload)
        
        # Check standard date fields at 5, 6, 7
        year_raw = decoded[5]
        month = decoded[6]
        day = decoded[7]
        
        # Heuristic for year
        year = year_raw
        if year == 0x1a: year = 2026
        elif year == 0x26: year = 2026 # Common offset/BCD?
        elif year < 50: year += 2000
        
        if month > 12 or day > 31 or month == 0 or day == 0:
            continue
            
        date_str = f"{year}-{month:02d}-{day:02d}"
        
        # Signature
        sig = decoded[:2].hex()
        
        # Extract potential steps/cals
        # For '6372' (History Summary)
        if sig == '6372':
            steps = int.from_bytes(decoded[15:17], 'little')
            cals = int.from_bytes(decoded[11:13], 'little') * 2
            dist = int.from_bytes(decoded[19:21], 'little') // 10
        # For '000f' (Live Update)
        elif sig == '000f':
            steps = int.from_bytes(decoded[15:17], 'little')
            cals = int.from_bytes(decoded[18:20], 'little')
            dist = int.from_bytes(decoded[20:22], 'little') // 10 if len(decoded) >= 22 else 0
        else:
            # Fallback: search for steps/cals pattern if possible
            steps = int.from_bytes(decoded[15:17], 'little')
            cals = 0
            dist = 0

        # Adjust date for user's timezone if it's "today"
        # User says 14th looks like 15th (UTC shift).
        # We'll calculate the actual local date by assuming the watch is UTC+0
        # and subtracting the user's offset (likely -5).
        # For now, let's just print the raw date and the "Adjusted" date.
        
        # Record only if steps or cals significant
        if steps > 0 or cals > 0:
            id_key = (date_str, steps, cals)
            if id_key not in unique_days:
                unique_days[id_key] = {
                    'date': date_str,
                    'steps': steps,
                    'cals': cals,
                    'dist': dist,
                    'sig': sig
                }

    print(f"{'Date (Watch)':<12} | {'Steps':<7} | {'Cals':<7} | {'Dist':<7} | {'Sig'}")
    print("-" * 60)
    
    sorted_recs = sorted(unique_days.values(), key=lambda x: x['date'], reverse=True)
    for r in sorted_recs:
        print(f"{r['date']:<12} | {r['steps']:<7} | {r['cals']:<7} | {r['dist']:<7} | {r['sig']}")

analyze_all_records('/home/izivkov/projects/gshock_api/src/tests/parsed.txt')
