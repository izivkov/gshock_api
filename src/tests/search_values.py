
def xor_decode(data, key=255):
    return bytes([b ^ key for b in data])

def search_val(decoded, val, name):
    print(f"Searching for {val} in {name}...")
    # Search for val as 2-byte LE
    for i in range(len(decoded) - 1):
        v = int.from_bytes(decoded[i:i+2], 'little')
        if v == val:
            print(f"  Found {val} at index {i} (LE)")
        v = int.from_bytes(decoded[i:i+2], 'big')
        if v == val:
            print(f"  Found {val} at index {i} (BE)")

b1 = "05FFF0FFFFFFE5FEF8F1DFC9BAFFFFFFFFFFFF41FDEF7B"
b2 = "059C8DFFFFFFD9FEF813A2D185FCFFA30BFBFFFFBFE0FFFFF0FF9FFFFFFFFF9DFFFFFFFFF0F0FFFFD8FFFFFFFFFEC9EFDAFEFFEECF009E010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101FF00A157FFCFFFC8FF9B00007E2B"

d1 = xor_decode(bytes.fromhex(b1)[1:])
d2 = xor_decode(bytes.fromhex(b2)[1:])

search_val(d1, 702, "Buffer 1")
search_val(d1, 0, "Buffer 1")
search_val(d2, 1268, "Buffer 2")
search_val(d2, 1780, "Buffer 2")

# Also search WITHOUT XOR
print("\nWITHOUT XOR:")
d1_raw = bytes.fromhex(b1)[1:]
d2_raw = bytes.fromhex(b2)[1:]
search_val(d1_raw, 702, "Buffer 1 Raw")
search_val(d2_raw, 1268, "Buffer 2 Raw")
search_val(d2_raw, 1780, "Buffer 2 Raw")
