
import re

def xor_decode(data, key=255):
    return bytes([b ^ key for b in data])

def analyze_all_history(file_path):
    with open(file_path, 'r') as f:
        content = f.read()

    notifies = re.findall(r'Notify Handle: 0x0013 Value: (05[0-9A-F]{30,})', content)
    
    for hex_str in notifies:
        data = bytes.fromhex(hex_str)
        payload = data[1:]
        decoded = xor_decode(payload)
        
        sig = decoded[:2].hex()
        # Look for date patterns anywhere
        dates = []
        for i in range(len(decoded)-3):
            if decoded[i] in [0x1a, 0x26] and decoded[i+1] == 0x01:
                dates.append(f"{decoded[i]:02x}-{decoded[i+1]:02x}-{decoded[i+2]:02x}")
        
        # Calculate sum of 16-bit values as a proxy for hourly data
        vals = []
        for i in range(8, len(decoded)-1, 4):
            val = int.from_bytes(decoded[i:i+2], 'little')
            if val != 0 and val != 0xffff:
                vals.append(val)
        
        if dates or vals:
            print(f"Sig: {sig} | Dates: {dates} | Sum: {sum(vals)} | Samples: {len(vals)}")
            # If it's a summary (6372)
            if sig == '6372':
                steps = int.from_bytes(decoded[15:17], 'little')
                cals = int.from_bytes(decoded[11:13], 'little') * 2
                print(f"  SUMMARY: Steps={steps}, Cals={cals}")

analyze_all_history('/home/izivkov/projects/gshock_api/src/tests/parsed.txt')
