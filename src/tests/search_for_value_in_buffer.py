#!/usr/bin/env python3
"""
G-Shock Health Data Buffer Search Tool
Searches for calorie values in different encodings throughout the buffer
"""

def search_value_in_buffer(hex_string, target_value, tolerance=10):
    """
    Search for a target value in a hex buffer using multiple encoding methods.
    
    Args:
        hex_string: Hex string without spaces (e.g., "6372000000260107...")
        target_value: The value to search for (e.g., 1780)
        tolerance: Search range +/- tolerance (default 10)
    """
    # Convert hex string to bytes
    buffer = bytes.fromhex(hex_string)
    buffer_len = len(buffer)
    
    print(f"Buffer length: {buffer_len} bytes")
    print(f"Searching for value: {target_value} (±{tolerance})")
    print("=" * 70)
    
    results = []
    
    # Search range
    min_val = target_value - tolerance
    max_val = target_value + tolerance
    
    # 1. Search as 16-bit little-endian
    print("\n[1] Searching as 16-bit Little-Endian (standard)...")
    for i in range(buffer_len - 1):
        value = int.from_bytes(buffer[i:i+2], byteorder='little', signed=False)
        if min_val <= value <= max_val:
            results.append({
                'offset': i,
                'value': value,
                'encoding': '16-bit LE',
                'bytes': f"0x{buffer[i]:02X} 0x{buffer[i+1]:02X}",
                'diff': abs(value - target_value)
            })
            print(f"  ✓ Found {value} at offset {i}: bytes [{buffer[i]:02X} {buffer[i+1]:02X}]")
    
    # 2. Search as 16-bit big-endian
    print("\n[2] Searching as 16-bit Big-Endian...")
    for i in range(buffer_len - 1):
        value = int.from_bytes(buffer[i:i+2], byteorder='big', signed=False)
        if min_val <= value <= max_val:
            results.append({
                'offset': i,
                'value': value,
                'encoding': '16-bit BE',
                'bytes': f"0x{buffer[i]:02X} 0x{buffer[i+1]:02X}",
                'diff': abs(value - target_value)
            })
            print(f"  ✓ Found {value} at offset {i}: bytes [{buffer[i]:02X} {buffer[i+1]:02X}]")
    
    # 3. Search as 32-bit little-endian
    print("\n[3] Searching as 32-bit Little-Endian...")
    for i in range(buffer_len - 3):
        value = int.from_bytes(buffer[i:i+4], byteorder='little', signed=False)
        if min_val <= value <= max_val:
            results.append({
                'offset': i,
                'value': value,
                'encoding': '32-bit LE',
                'bytes': f"0x{buffer[i]:02X} 0x{buffer[i+1]:02X} 0x{buffer[i+2]:02X} 0x{buffer[i+3]:02X}",
                'diff': abs(value - target_value)
            })
            print(f"  ✓ Found {value} at offset {i}: bytes [{buffer[i]:02X} {buffer[i+1]:02X} {buffer[i+2]:02X} {buffer[i+3]:02X}]")
    
    # 4. Search as 32-bit big-endian
    print("\n[4] Searching as 32-bit Big-Endian...")
    for i in range(buffer_len - 3):
        value = int.from_bytes(buffer[i:i+4], byteorder='big', signed=False)
        if min_val <= value <= max_val:
            results.append({
                'offset': i,
                'value': value,
                'encoding': '32-bit BE',
                'bytes': f"0x{buffer[i]:02X} 0x{buffer[i+1]:02X} 0x{buffer[i+2]:02X} 0x{buffer[i+3]:02X}",
                'diff': abs(value - target_value)
            })
            print(f"  ✓ Found {value} at offset {i}: bytes [{buffer[i]:02X} {buffer[i+1]:02X} {buffer[i+2]:02X} {buffer[i+3]:02X}]")
    
    # 5. Search as scaled values (divided by 10, 100, etc.)
    print("\n[5] Searching for scaled values...")
    for i in range(buffer_len - 1):
        value_16le = int.from_bytes(buffer[i:i+2], byteorder='little', signed=False)
        
        # Check value * 10
        if min_val <= value_16le * 10 <= max_val:
            results.append({
                'offset': i,
                'value': value_16le * 10,
                'encoding': '16-bit LE * 10',
                'bytes': f"0x{buffer[i]:02X} 0x{buffer[i+1]:02X} (stored as {value_16le})",
                'diff': abs(value_16le * 10 - target_value)
            })
            print(f"  ✓ Found {value_16le * 10} at offset {i}: stored as {value_16le}, multiply by 10")
        
        # Check value * 100
        if min_val <= value_16le * 100 <= max_val:
            results.append({
                'offset': i,
                'value': value_16le * 100,
                'encoding': '16-bit LE * 100',
                'bytes': f"0x{buffer[i]:02X} 0x{buffer[i+1]:02X} (stored as {value_16le})",
                'diff': abs(value_16le * 100 - target_value)
            })
            print(f"  ✓ Found {value_16le * 100} at offset {i}: stored as {value_16le}, multiply by 100")
    
    # 6. Search for sum of consecutive bytes
    print("\n[6] Searching for sums of consecutive values...")
    window_sizes = [2, 3, 4, 5]
    for window in window_sizes:
        for i in range(buffer_len - window + 1):
            # Sum as individual bytes
            byte_sum = sum(buffer[i:i+window])
            if min_val <= byte_sum <= max_val:
                bytes_str = ' '.join(f"0x{b:02X}" for b in buffer[i:i+window])
                results.append({
                    'offset': i,
                    'value': byte_sum,
                    'encoding': f'Sum of {window} bytes',
                    'bytes': bytes_str,
                    'diff': abs(byte_sum - target_value)
                })
                print(f"  ✓ Found {byte_sum} at offset {i}: sum of bytes [{bytes_str}]")
    
    # Print summary
    print("\n" + "=" * 70)
    print(f"\nSUMMARY: Found {len(results)} potential matches")
    
    if results:
        # Sort by closest match
        results.sort(key=lambda x: x['diff'])
        print("\nTop 5 closest matches:")
        for i, result in enumerate(results[:5], 1):
            print(f"\n  {i}. Offset {result['offset']} (diff: {result['diff']})")
            print(f"     Value: {result['value']}")
            print(f"     Encoding: {result['encoding']}")
            print(f"     Bytes: {result['bytes']}")
    else:
        print("\nNo matches found. Try:")
        print("  1. Increasing tolerance")
        print("  2. Checking if the buffer and screenshot were captured at the same time")
        print("  3. Looking for the value in a different format")
    
    return results


# Example usage
if __name__ == "__main__":
    # Buffer 2 from your logs (Jan 6 History - expecting Steps 1268, Cal 1780)
    buffer2_hex = "6372000000260107ec5d2e7a03005cf4040000401f00000f00600000000062000000000f0f000027000000000136102501001130ff61fefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefe00ff5ea8003000370064ffff81d4"
    
    print("=" * 70)
    print("G-SHOCK HEALTH DATA BUFFER SEARCH")
    print("=" * 70)
    print("\nAnalyzing Buffer 2 (Historical Data)")
    print(f"Raw hex: {buffer2_hex[:60]}...")
    print()
    
    # Search for calories value 1780
    results = search_value_in_buffer(buffer2_hex, target_value=1780, tolerance=10)
    
    print("\n" + "=" * 70)
    print("\nYou can modify the script to:")
    print("  - Change target_value to search for different values")
    print("  - Adjust tolerance (currently ±10)")
    print("  - Add your own buffer hex string")
    print("  - Add custom encoding search patterns")