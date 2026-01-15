
def xor_decode(data, key=255):
    return bytes([b ^ key for b in data])

b1 = "05FFF0FFFFFFE5FEF8F1DFC9BAFFFFFFFFFFFF41FDEF7B"
b2 = "059C8DFFFFFFD9FEF813A2D185FCFFA30BFBFFFFBFE0FFFFF0FF9FFFFFFFFF9DFFFFFFFFF0F0FFFFD8FFFFFFFFFEC9EFDAFEFFEECF009E010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101FF00A157FFCFFFC8FF9B00007E2B"

def print_decoded(hex_str, name):
    data = bytes.fromhex(hex_str)
    payload = data[1:]
    decoded = xor_decode(payload)
    print(f"--- {name} ---")
    print(f"Raw: {payload.hex()}")
    print(f"Decoded: {decoded.hex()}")
    # Print with indices
    for i in range(0, len(decoded), 16):
        chunk = decoded[i:i+16]
        hex_chunk = " ".join(f"{b:02x}" for b in chunk)
        print(f"{i:03d}: {hex_chunk}")

print_decoded(b1, "Buffer 1")
print_decoded(b2, "Buffer 2")
