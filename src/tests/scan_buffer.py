
def xor_decode(data, key=255):
    return bytes([b ^ key for b in data])

b2 = "059C8DFFFFFFD9FEF813A2D185FCFFA30BFBFFFFBFE0FFFFF0FF9FFFFFFFFF9DFFFFFFFFF0F0FFFFD8FFFFFFFFFEC9EFDAFEFFEECF009E010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101FF00A157FFCFFFC8FF9B00007E2B"
decoded = xor_decode(bytes.fromhex(b2)[1:])

print(f"Decoded Length: {len(decoded)}")
for i in range(len(decoded)-16):
    # Search for date pattern: 26 01 [Day]
    if decoded[i] == 0x26 and decoded[i+1] == 0x01:
        day = decoded[i+2]
        # Try to find steps/cals relative to this date
        # In history summary, cals are at +6, steps at +10
        cals_raw = int.from_bytes(decoded[i+6:i+8], 'little')
        steps = int.from_bytes(decoded[i+10:i+12], 'little')
        print(f"Found Date at {i}: 2026-01-{day:02d} | RawCals={cals_raw} (x2={cals_raw*2}) | Steps={steps}")

# Search for other days even without 26 01
print("\nSearching for any potential Day markers (10..15) at start of blocks...")
for i in range(0, len(decoded)-12, 12):
    day = decoded[i+7] # Try offset 7
    if 1 <= day <= 31: 
        print(f"Possible record at {i}: Day={day}")
