#!/usr/bin/env python3
"""
G-Shock Buffer Structure Analyzer
Analyzes buffer patterns, identifies repeating structures, and decodes potential data
"""

def analyze_buffer(hex_string):
    """
    Comprehensive analysis of a G-Shock health data buffer.
    """
    # Remove any spaces and convert to bytes
    hex_clean = hex_string.replace(" ", "")
    buffer = bytes.fromhex(hex_clean)
    buffer_len = len(buffer)
    
    print("=" * 80)
    print("G-SHOCK BUFFER ANALYSIS")
    print("=" * 80)
    print(f"\nBuffer length: {buffer_len} bytes ({buffer_len * 8} bits)")
    print(f"Hex string: {hex_clean[:80]}{'...' if len(hex_clean) > 80 else ''}")
    print()
    
    # 1. HEADER ANALYSIS (first 8 bytes)
    print("=" * 80)
    print("HEADER ANALYSIS (First 8 bytes)")
    print("=" * 80)
    if buffer_len >= 8:
        header = buffer[:8]
        print(f"Raw bytes: {' '.join(f'{b:02X}' for b in header)}")
        print(f"\nByte 0: 0x{header[0]:02X} ({header[0]}) - Could be: message type, command ID")
        print(f"Byte 1: 0x{header[1]:02X} ({header[1]})")
        print(f"Bytes 0-1 as 16-bit LE: {int.from_bytes(header[0:2], 'little')}")
        print(f"Bytes 0-3 as 32-bit LE: {int.from_bytes(header[0:4], 'little')}")
        print(f"Bytes 4-7: {' '.join(f'{b:02X}' for b in header[4:8])}")
        
        # Check if looks like a timestamp or magic number
        val_32 = int.from_bytes(header[0:4], 'little')
        if val_32 > 1000000000 and val_32 < 2000000000:
            print(f"  → Bytes 0-3 might be a Unix timestamp: {val_32}")
    
    # 2. PATTERN DETECTION
    print("\n" + "=" * 80)
    print("PATTERN DETECTION")
    print("=" * 80)
    
    # Find repeating byte sequences
    repeating_patterns = {}
    for pattern_len in [2, 4, 8]:
        for i in range(buffer_len - pattern_len):
            pattern = buffer[i:i+pattern_len]
            pattern_hex = pattern.hex().upper()
            
            # Count occurrences
            count = 0
            pos = 0
            positions = []
            while pos < buffer_len - pattern_len:
                if buffer[pos:pos+pattern_len] == pattern:
                    positions.append(pos)
                    count += 1
                pos += 1
            
            if count > 3:  # Only show patterns that repeat 3+ times
                if pattern_hex not in repeating_patterns:
                    repeating_patterns[pattern_hex] = {
                        'length': pattern_len,
                        'count': count,
                        'positions': positions[:10]  # First 10 positions
                    }
    
    if repeating_patterns:
        # Sort by frequency
        sorted_patterns = sorted(repeating_patterns.items(), key=lambda x: x[1]['count'], reverse=True)
        print(f"\nFound {len(sorted_patterns)} repeating patterns:")
        for i, (pattern, info) in enumerate(sorted_patterns[:5], 1):
            print(f"\n{i}. Pattern: {pattern} ({info['length']} bytes)")
            print(f"   Occurrences: {info['count']}")
            print(f"   First positions: {', '.join(map(str, info['positions'][:8]))}")
            
            # Check if it's a null/empty pattern
            if pattern == 'FF' * info['length']:
                print(f"   → This is all 0xFF (empty/uninitialized data)")
            elif pattern == '00' * info['length']:
                print(f"   → This is all 0x00 (null/padding)")
    
    # 3. STRUCTURE DETECTION - Check for repeating record structure
    print("\n" + "=" * 80)
    print("REPEATING STRUCTURE DETECTION")
    print("=" * 80)
    
    # Check for fixed-size records
    for record_size in [4, 6, 8, 10, 12, 16, 24]:
        if buffer_len % record_size == 0:
            num_records = buffer_len // record_size
            print(f"\n✓ Buffer divides evenly into {num_records} records of {record_size} bytes each")
            
            # Show first few records
            print(f"  First 5 records:")
            for i in range(min(5, num_records)):
                record = buffer[i*record_size:(i+1)*record_size]
                record_hex = ' '.join(f'{b:02X}' for b in record)
                print(f"    Record {i}: {record_hex}")
                
                # Decode as different types
                if record_size >= 2:
                    val_16le = int.from_bytes(record[0:2], 'little')
                    print(f"              First 2 bytes as 16-bit LE: {val_16le}")
                if record_size >= 4:
                    val_32le = int.from_bytes(record[0:4], 'little')
                    print(f"              First 4 bytes as 32-bit LE: {val_32le}")
    
    # 4. VALUE DISTRIBUTION ANALYSIS
    print("\n" + "=" * 80)
    print("VALUE DISTRIBUTION")
    print("=" * 80)
    
    # Analyze all 16-bit LE values
    values_16le = []
    for i in range(buffer_len - 1):
        val = int.from_bytes(buffer[i:i+2], 'little')
        values_16le.append((i, val))
    
    # Find interesting values (non-zero, not 0xFFFF)
    interesting = [(i, v) for i, v in values_16le if v != 0 and v != 0xFFFF and v < 10000]
    
    print(f"\nInteresting 16-bit LE values (non-zero, non-0xFFFF, < 10000):")
    for i, (offset, value) in enumerate(interesting[:20], 1):
        print(f"  Offset {offset:3d}: {value:5d} (0x{value:04X}) - bytes [{buffer[offset]:02X} {buffer[offset+1]:02X}]")
        
        # Suggest what it might be
        if 0 < value < 100:
            print(f"              → Could be: hour, percentage, small count")
        elif 100 <= value < 500:
            print(f"              → Could be: calories (scaled), distance meters")
        elif 500 <= value < 2000:
            print(f"              → Could be: calories, steps (scaled)")
        elif 2000 <= value < 30000:
            print(f"              → Could be: steps, distance meters")
    
    # 5. SPECIFIC VALUE SEARCH
    print("\n" + "=" * 80)
    print("COMMON HEALTH VALUES SEARCH")
    print("=" * 80)
    
    # Common ranges for health data
    searches = [
        ("Steps (0-30000)", 0, 30000),
        ("Calories (0-5000)", 0, 5000),
        ("Heart Rate (30-220)", 30, 220),
        ("Distance km*10 (0-500)", 0, 500),
    ]
    
    for name, min_val, max_val in searches:
        matches = [(i, v) for i, v in values_16le if min_val <= v <= max_val]
        if matches:
            print(f"\n{name}: Found {len(matches)} values in range")
            for offset, value in matches[:5]:
                print(f"  Offset {offset}: {value}")
    
    # 6. ENTROPY/RANDOMNESS CHECK
    print("\n" + "=" * 80)
    print("DATA DENSITY ANALYSIS")
    print("=" * 80)
    
    # Count 0xFF and 0x00 bytes
    ff_count = buffer.count(0xFF)
    zero_count = buffer.count(0x00)
    data_bytes = buffer_len - ff_count - zero_count
    
    print(f"0xFF bytes: {ff_count} ({ff_count/buffer_len*100:.1f}%)")
    print(f"0x00 bytes: {zero_count} ({zero_count/buffer_len*100:.1f}%)")
    print(f"Data bytes: {data_bytes} ({data_bytes/buffer_len*100:.1f}%)")
    
    if ff_count > buffer_len * 0.5:
        print("\n⚠ Warning: Buffer is >50% 0xFF - likely contains empty/uninitialized data")
    
    return buffer


# Main execution
if __name__ == "__main__":
    # Your new buffer
    buffer_hex = "059C8DFFFFFFD9FEF813A2D185FCFFA30BFBFFFFBFE0FFFFF0FF9FFFFFFFFF9DFFFFFFFFF0F0FFFFD8FFFFFFFFFEC9EFDAFEFFEECF009E010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101FF00A157FFCFFFC8FF9B00007E2B"
    
    buffer = analyze_buffer(buffer_hex)
    
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print("\nKey Observations:")
    print("1. Check the HEADER section for message type/command identifiers")
    print("2. Look at REPEATING STRUCTURE to understand the record format")
    print("3. Review INTERESTING VALUES for potential health metrics")
    print("4. If buffer is mostly 0xFF, it may be empty/uninitialized")