
import re

def xor_decode(data, key=255):
    return bytes([b ^ key for b in data])

def find_all_dates(file_path):
    with open(file_path, 'r') as f:
        content = f.read()

    notifies = re.findall(r'Value: (05[0-9A-F]+)', content)
    
    unique_dates = {}

    for hex_str in notifies:
        data = bytes.fromhex(hex_str)
        if len(data) < 20: continue
        
        payload = data[1:]
        decoded = xor_decode(payload)
        
        # Look for 2026-01 (1a 01 or 26 01)
        for i in range(len(decoded)-3):
            if decoded[i] in [0x1a, 0x26] and decoded[i+1] == 0x01:
                year = decoded[i]
                month = decoded[i+1]
                day = decoded[i+2]
                
                if 1 <= month <= 12 and 1 <= day <= 31:
                    date_str = f"20{year:02x}-{month:02d}-{day:02d}"
                    
                    # Try to extract steps relative to this date
                    # If it's a summary record, steps are at offset + 10 (LE)
                    # Let's check a range around it.
                    record_context = decoded[i:i+30].hex()
                    
                    if date_str not in unique_dates:
                        unique_dates[date_str] = []
                    unique_dates[date_str].append(record_context)

    for d in sorted(unique_dates.keys()):
        print(f"Date: {d}")
        for ctx in unique_dates[d]:
            print(f"  Context: {ctx}")

find_all_dates('/home/izivkov/projects/gshock_api/src/tests/parsed.txt')
