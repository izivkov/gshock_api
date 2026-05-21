#!/usr/bin/env python3
"""
Verify the health data decode logic against known expected values from screenshots.

Expected values from screenshots:
  Jan 7:  Steps=0,    Cal=702   (Live, 9:32 AM)
  Jan 6:  Steps=1268, Cal=1780  (History, 63 72)
"""

def xor_decode(data: bytes, key: int = 255) -> bytes:
    return bytes([b ^ key for b in data])

print("=" * 70)
print("VERIFICATION: Live Update (Jan 7, Steps=0, Cal=702)")
print("=" * 70)

# Live update buffer
data = bytearray.fromhex("05FFF0FFFFFFE5FEF8F1DFC9BAFFFFFFFFFFFF41FDEF7B")
payload = data[1:]
decoded = xor_decode(payload)

print(f"Decoded: {decoded.hex()}")
# decoded = 000f0000001a01070e203645000000000000be021084
#                      Y  M  D  H  M
# [0]  = 0x00 (type byte 1)
# [1]  = 0x0f (type byte 2) => signature 000f
# [5]  = 0x1a (26 = year 2026)
# [6]  = 0x01 (month 1)
# [7]  = 0x07 (day 7)
# [8]  = 0x0e (hour 14 - but wait, BCD(0x0e) doesn't work, hex 14 is 0x0e)
# [9]  = 0x20 (minute 32? BCD: 20. hex: 32)
# [10] = 0x36 (unknown, value 54)
# [11] = 0x45 (unknown, value 69)
# Steps = [15:17] LE = 0x0000 = 0 ✓
# [18:20] LE = decoded[18] + decoded[19]*256 = 0xbe + 0x02*256 = 190 + 512 = 702 ✓ CALORIES!

steps = int.from_bytes(decoded[15:17], 'little')
calories = int.from_bytes(decoded[18:20], 'little')
print(f"Steps [15:17]:    {steps}  (expected: 0)     {'✓' if steps == 0 else '✗'}")
print(f"Calories [18:20]: {calories}  (expected: 702)   {'✓' if calories == 702 else '✗'}")

# Now check the second and third live snapshots (different timestamps, calories should change)
for name, hex_str in [("Live_Jan7_b", "05FFF0FFFFFFE5FEF8F1DF85FFFFFFFFFFFFFF40FD827E"),
                       ("Live_Jan7_c", "05FFF0FFFFFFE5FEF8F1DD8EFFFFFFFFFFFFFF3EFD34A2")]:
    d = bytearray.fromhex(hex_str)
    dec = xor_decode(d[1:])
    s = int.from_bytes(dec[15:17], 'little')
    c = int.from_bytes(dec[18:20], 'little')
    print(f"\n{name}: Steps={s}, Cal={c}")
    print(f"  Time: {dec[5]+2000}-{dec[6]:02d}-{dec[7]:02d} {dec[8]:02d}:{dec[9]:02d}")

print(f"\n{'='*70}")
print("VERIFICATION: History Record (Jan 6, Steps=1268, Cal=1780)")
print("=" * 70)

# History buffer
data = bytearray.fromhex("059C8DFFFFFFD9FEF813A2D185FCFFA30BFBFFFFBFE0FFFFF0FF9FFFFFFFFF9DFFFFFFFFF0F0FFFFD8FFFFFFFFFEC9EFDAFEFFEECF009E010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101FF00A157FFCFFFC8FF9B00007E2B")
payload = data[1:]
decoded = xor_decode(payload)

print(f"Decoded first 25: {decoded[:25].hex()}")
# decoded = 6372000000260107ec5d2e7a03005cf4040000401f00000f00...
#                      Y  M  D
# [0]  = 0x63 (type byte 1)
# [1]  = 0x72 (type byte 2) => signature 6372
# [5]  = 0x26 (38 = year, 0x26 = 2026 when treated as hex year code)
# [6]  = 0x01 (month 1)
# [7]  = 0x07 (day 7) => BUT the data is for Jan 6 (date - 1 day)
# [11] = 0x7a, [12] = 0x03 => LE = 890 => 890 * 2 = 1780 ✓ CALORIES!
# [15] = 0xf4, [16] = 0x04 => LE = 1268 ✓ STEPS!

year = decoded[5]
if year == 0x26:
    year = 2026
month = decoded[6]
day = decoded[7]
print(f"Header date: {year}-{month:02d}-{day:02d}")
print(f"Actual data date (day-1): {year}-{month:02d}-{day-1:02d}")

calories_raw = int.from_bytes(decoded[11:13], 'little')
calories = calories_raw * 2
steps = int.from_bytes(decoded[15:17], 'little')
distance = int.from_bytes(decoded[19:21], 'little') // 10

print(f"Calories_raw [11:13]: {calories_raw}  x2 = {calories}  (expected: 1780) {'✓' if calories == 1780 else '✗'}")
print(f"Steps [15:17]:        {steps}  (expected: 1268) {'✓' if steps == 1268 else '✗'}")
print(f"Distance [19:21]:     {distance}m")

print(f"\n{'='*70}")
print("SUMMARY OF DECODE FORMAT")
print("=" * 70)
print("""
LIVE UPDATE (signature 000f):
  [0:2]   = Signature: 0x00 0x0f
  [5]     = Year (hex, e.g. 0x1a = 26 -> 2026)
  [6]     = Month
  [7]     = Day
  [8]     = Hour (hex)
  [9]     = Minute (hex)
  [15:17] = Steps (16-bit LE)
  [18:20] = Calories (16-bit LE, direct value)

HISTORY RECORD (signature 6372):
  [0:2]   = Signature: 0x63 0x72
  [5]     = Year (0x26 = 2026)
  [6]     = Month
  [7]     = Day (NOTE: this is day+1, actual data date is day-1)
  [11:13] = Calories/2 (16-bit LE, multiply by 2)
  [15:17] = Steps (16-bit LE)
  [19:21] = Distance in decimeters (16-bit LE, divide by 10 for meters)
""")

# Now let's also verify the other buffer type (65 63)
print("=" * 70)
print("ANALYSIS: Buffer type 6563 (second history buffer)")
print("=" * 70)

data = bytearray.fromhex("059A9CFFFFFFA40100000001010001009FFFFFFFFF9DFFFFFFFFFFFFFFFFF6FFFFFFFFFFF8F6EAF9FFFFEF9E010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101FFA17EFFBAFFC8FF49B7")
payload = data[1:]
decoded = xor_decode(payload)
print(f"Decoded first 35: {decoded[:35].hex()}")
# decoded = 65630000005bfefffffffefefffeff60000000006200000000000000000900000000000709150600001061...
# [0:2] = 0x65 0x63 => signature "6563"
# [5]   = 0x5b (91) => not a valid year...
# This could be a different buffer type with different date encoding
# Let me check if bytes 5-7 could be something else

# Check: maybe this is NOT a date at 5,6,7 but rather has a different structure
# The date might be encoded elsewhere
# Let's look at the tail
tail = decoded[-10:]
print(f"Tail bytes: {tail.hex()}")
for i, b in enumerate(tail):
    print(f"  [{len(decoded)-10+i}] 0x{b:02x} ({b})")

# Let's check offset 15 for steps
print(f"\nOffset 15-16 (LE): {int.from_bytes(decoded[15:17], 'little')}")
print(f"Offset 11-12 (LE): {int.from_bytes(decoded[11:13], 'little')}")
print(f"Offset 11-12 (LE)*2: {int.from_bytes(decoded[11:13], 'little') * 2}")
