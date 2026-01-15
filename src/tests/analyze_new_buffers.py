
def xor_decode(data, key=255):
    return bytes([b ^ key for b in data])

# Buffer 1 from Step 88 (Jan 15 Watch = Jan 14 Local)
b1_88 = "05fff0ffffffe5fef0fedbe94cffffffffffffb8f9214f"
# Buffer 2 from Step 88 (Signature 6563)
b2_88 = "059a9cffffffa40100000001010001009fffffffff9dfffffffffffffffff2ffffffffffffebe4e8fffff29e010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101ffa19cffbaffc8ffb7a3"

d1 = xor_decode(bytes.fromhex(b1_88)[1:])
d2 = xor_decode(bytes.fromhex(b2_88)[1:])

print(f"B1 Decoded: {d1.hex()}")
print(f"B2 Decoded: {d2.hex()}")

def print_le16(decoded):
    for i in range(len(decoded)-1):
        val = int.from_bytes(decoded[i:i+2], 'little')
        if val > 100:
            print(f"  Offset {i:2d}: {val:5d} (0x{val:04x})")

print("Candidates for B1 (Today):")
print_le16(d1)
print("Candidates for B2 (History):")
print_le16(d2)
