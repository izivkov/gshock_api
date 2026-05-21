#!/usr/bin/env python3
"""
Decode all health data buffers from the BT HCI log to cross-reference
against the screenshot expected values.

Expected values from screenshots:
  Jan 14: Steps=0, Cal=1625 (Screenshot_20260114-204802.png)
  Jan 13: Steps=0, Cal=1766
  Jan  7: Steps=0, Cal=702
  Jan  6: Steps=1268, Cal=1780
  Jan  5: Steps=42, Cal=1763
  Jan  4: Steps=0, Cal=1704
  Jan  3: Steps=0, Cal=1701
  Jan  2: Steps=13, Cal=1925
"""

import re
from datetime import datetime, timedelta

def xor_decode(data: bytes, key: int = 255) -> bytes:
    return bytes([b ^ key for b in data])

def bcd_to_int(bcd: int) -> int:
    return ((bcd >> 4) * 10) + (bcd & 0x0F)

# Expected values from screenshots
EXPECTED = {
    "2026-01-14": {"steps": 0, "calories": 1625},
    "2026-01-13": {"steps": 0, "calories": 1766},
    "2026-01-07": {"steps": 0, "calories": 702},
    "2026-01-06": {"steps": 1268, "calories": 1780},
    "2026-01-05": {"steps": 42, "calories": 1763},
    "2026-01-04": {"steps": 0, "calories": 1704},
    "2026-01-03": {"steps": 0, "calories": 1701},
    "2026-01-02": {"steps": 13, "calories": 1925},
}

# Key buffers from the parsed.txt (Handle 0x0013, starting with 05)
# These are the first/header packets of each health data transfer
health_buffers = {
    # Line 99: Live update (current day Jan 7, 9:32 AM)
    "Live_Jan7_9:32a": "05FFF0FFFFFFE5FEF8F1DFC9BAFFFFFFFFFFFF41FDEF7B",
    # Line 224: History record for Jan 6 (index 63 72)
    "Hist_63_Jan6": "059C8DFFFFFFD9FEF813A2D185FCFFA30BFBFFFFBFE0FFFFF0FF9FFFFFFFFF9DFFFFFFFFF0F0FFFFD8FFFFFFFFFEC9EFDAFEFFEECF009E010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101FF00A157FFCFFFC8FF9B00007E2B",
    # Line 106: Another buffer (index 65 63)
    "Buf_65_63": "059A9CFFFFFFA40100000001010001009FFFFFFFFF9DFFFFFFFFFFFFFFFFF6FFFFFFFFFFF8F6EAF9FFFFEF9E010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101FFA17EFFBAFFC8FF49B7",
    # Line 321: Second Live update (Jan 7, later)
    "Live_Jan7_b": "05FFF0FFFFFFE5FEF8F1DF85FFFFFFFFFFFFFF40FD827E",
    # Line 440: Third Live update (Jan 7, later)
    "Live_Jan7_c": "05FFF0FFFFFFE5FEF8F1DD8EFFFFFFFFFFFFFF3EFD34A2",
    # Line 207: Short buffer
    "Short_5A": "05A5C3FFFFFFD9FEF813F7010101010000000101010001000100010001000000010000000101010101010100000001010101010101010101010101",
    # Line 215: Short buffer
    "Short_5B": "05A4ECFFFFFFD9FEF813010000000101000100F7B06F",
}

print("=" * 80)
print("G-SHOCK HEALTH DATA BUFFER ANALYSIS")
print("=" * 80)

for name, hex_str in health_buffers.items():
    data = bytearray.fromhex(hex_str)
    payload = data[1:]  # strip leading 05
    decoded = xor_decode(payload)
    
    print(f"\n{'='*60}")
    print(f"Buffer: {name}")
    print(f"  Raw payload hex: {payload.hex()}")
    print(f"  Decoded hex:     {decoded.hex()}")
    print(f"  Decoded length:  {len(decoded)} bytes")
    
    if len(decoded) < 10:
        print("  TOO SHORT")
        continue
    
    # Show first 30 bytes with offsets
    print(f"  Byte-by-byte (decoded):")
    for i in range(min(30, len(decoded))):
        b = decoded[i]
        print(f"    [{i:2d}] 0x{b:02x} ({b:3d})  char='{chr(b) if 32 <= b < 127 else '.'}'")
    
    # Signature
    sig = f"{decoded[0]:02x}{decoded[1]:02x}"
    print(f"\n  Signature: {sig}")
    
    # Date at 5,6,7
    y_raw, m_raw, d_raw = decoded[5], decoded[6], decoded[7]
    print(f"  Date bytes [5,6,7]: 0x{y_raw:02x}({y_raw}), 0x{m_raw:02x}({m_raw}), 0x{d_raw:02x}({d_raw})")
    
    # Try BCD date
    try:
        y_bcd = 2000 + bcd_to_int(y_raw)
        m_bcd = bcd_to_int(m_raw)
        d_bcd = bcd_to_int(d_raw)
        if 1 <= m_bcd <= 12 and 1 <= d_bcd <= 31:
            print(f"  Date (BCD): {y_bcd}-{m_bcd:02d}-{d_bcd:02d}")
    except:
        pass
    
    # Try hex date
    try:
        y_hex = 2000 + y_raw
        if 1 <= m_raw <= 12 and 1 <= d_raw <= 31:
            print(f"  Date (hex): {y_hex}-{m_raw:02d}-{d_raw:02d}")
    except:
        pass
    
    # Try different value interpretations
    print(f"\n  --- 16-bit LE value scan (decoded) ---")
    for off in range(8, min(30, len(decoded) - 1)):
        val = int.from_bytes(decoded[off:off+2], 'little')
        val2 = val * 2
        if val > 0 and val < 30000:
            markers = []
            for date, expected in EXPECTED.items():
                if val == expected["steps"]:
                    markers.append(f"STEPS match {date}")
                if val == expected["calories"]:
                    markers.append(f"CALORIES match {date}")
                if val2 == expected["calories"]:
                    markers.append(f"CALORIES/2 match {date}")
            mark_str = f"  *** {', '.join(markers)}" if markers else ""
            print(f"    offset {off:2d}: {val:5d}  (x2={val2:5d}){mark_str}")

print("\n\n" + "=" * 80)
print("DETAILED ANALYSIS OF HISTORY BUFFER (Jan 6, Steps=1268, Cal=1780)")
print("=" * 80)

# Focus on the Jan 6 history buffer
data = bytearray.fromhex("059C8DFFFFFFD9FEF813A2D185FCFFA30BFBFFFFBFE0FFFFF0FF9FFFFFFFFF9DFFFFFFFFF0F0FFFFD8FFFFFFFFFEC9EFDAFEFFEECF009E010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101FF00A157FFCFFFC8FF9B00007E2B")
payload = data[1:]
decoded = xor_decode(payload)

print(f"Full decoded hex: {decoded.hex()}")
print(f"\nSearching for value 1780 (0x06F4):")
target = 1780
for i in range(len(decoded) - 1):
    val_le = int.from_bytes(decoded[i:i+2], 'little')
    val_be = int.from_bytes(decoded[i:i+2], 'big')
    if val_le == target:
        print(f"  FOUND {target} at offset {i} (LE): bytes [{decoded[i]:02x} {decoded[i+1]:02x}]")
    if val_be == target:
        print(f"  FOUND {target} at offset {i} (BE): bytes [{decoded[i]:02x} {decoded[i+1]:02x}]")
    if val_le * 2 == target:
        print(f"  FOUND {target}÷2={val_le} at offset {i} (LE*2): bytes [{decoded[i]:02x} {decoded[i+1]:02x}]")

print(f"\nSearching for value 1268 (0x04F4):")
target = 1268
for i in range(len(decoded) - 1):
    val_le = int.from_bytes(decoded[i:i+2], 'little')
    if val_le == target:
        print(f"  FOUND {target} at offset {i} (LE): bytes [{decoded[i]:02x} {decoded[i+1]:02x}]")

print(f"\nSearching for value 890 (1780/2):")
target = 890
for i in range(len(decoded) - 1):
    val_le = int.from_bytes(decoded[i:i+2], 'little')
    if val_le == target:
        print(f"  FOUND {target} at offset {i} (LE): bytes [{decoded[i]:02x} {decoded[i+1]:02x}]")


print("\n\n" + "=" * 80)
print("ANALYSIS OF LIVE UPDATE BUFFERS (Jan 7)")
print("=" * 80)

for name in ["Live_Jan7_9:32a", "Live_Jan7_b", "Live_Jan7_c"]:
    hex_str = health_buffers[name]
    data = bytearray.fromhex(hex_str)
    payload = data[1:]
    decoded = xor_decode(payload)
    
    print(f"\n--- {name} ---")
    print(f"Decoded hex: {decoded.hex()}")
    
    print(f"Searching for value 702 (0x02BE):")
    target = 702
    for i in range(len(decoded) - 1):
        val_le = int.from_bytes(decoded[i:i+2], 'little')
        if val_le == target:
            print(f"  FOUND {target} at offset {i} (LE): bytes [{decoded[i]:02x} {decoded[i+1]:02x}]")
        if val_le * 2 == target:
            print(f"  FOUND {target}÷2={val_le} at offset {i} (LE*2): bytes [{decoded[i]:02x} {decoded[i+1]:02x}]")
    
    # Also try searching in the raw payload (not XOR decoded)
    print(f"Searching for 702 in RAW payload (not XOR decoded):")
    for i in range(len(payload) - 1):
        val_le = int.from_bytes(payload[i:i+2], 'little')
        if val_le == target:
            print(f"  FOUND {target} at offset {i} (LE RAW): bytes [{payload[i]:02x} {payload[i+1]:02x}]")


print("\n\n" + "=" * 80)
print("ANALYSIS OF 65 63 BUFFER (possible Jan 5/6 data)")
print("=" * 80)
data = bytearray.fromhex("059A9CFFFFFFA40100000001010001009FFFFFFFFF9DFFFFFFFFFFFFFFFFF6FFFFFFFFFFF8F6EAF9FFFFEF9E010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101FFA17EFFBAFFC8FF49B7")
payload = data[1:]
decoded = xor_decode(payload)
print(f"Decoded hex: {decoded.hex()}")
print(f"Byte-by-byte (first 30):")
for i in range(min(30, len(decoded))):
    b = decoded[i]
    print(f"  [{i:2d}] 0x{b:02x} ({b:3d})")

# Search for any expected calorie values
for date, expected in sorted(EXPECTED.items()):
    cal = expected["calories"]
    steps = expected["steps"]
    for i in range(len(decoded) - 1):
        val_le = int.from_bytes(decoded[i:i+2], 'little')
        if val_le == cal:
            print(f"  FOUND cal={cal} ({date}) at offset {i} (LE)")
        if val_le * 2 == cal:
            print(f"  FOUND cal={cal}÷2={val_le} ({date}) at offset {i} (LE*2)")
        if val_le == steps and steps > 0:
            print(f"  FOUND steps={steps} ({date}) at offset {i} (LE)")
