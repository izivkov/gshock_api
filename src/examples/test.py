import struct

def parse_btsnoop(path):
    with open(path, 'rb') as f:
        f.read(16)
        records = []
        while True:
            hdr = f.read(24)
            if len(hdr) < 24:
                break
            orig_len, inc_len, flags, drops, ts = struct.unpack('>IIIIq', hdr)
            data = f.read(inc_len)
            records.append((flags, data, ts))
    return records

records = parse_btsnoop("/home/izivkov/projects/gshock_api/src/examples/btsnoop_hci_bx.log")

# Read By Type responses [1123-1138] contain property flags for each characteristic
# Property byte is at a fixed offset in the response
# Format: length(1) | handle(2) | properties(1) | value_handle(2) | uuid(N)
print("=== Characteristic properties from GATT discovery ===")
for i in range(1120, 1145):
    flags, data, ts = records[i]
    if data and data[0] == 0x02 and len(data) >= 10:
        att = data[9:]
        if att and att[0] == 0x09 and (flags & 1):
            body = att[2:]  # skip opcode + length
            item_len = att[1]
            for j in range(0, len(body), item_len):
                item = body[j:j+item_len]
                if len(item) < 3:
                    continue
                decl_handle = int.from_bytes(item[0:2], 'little')
                props = item[2]
                val_handle = int.from_bytes(item[3:5], 'little') if len(item) >= 5 else 0
                prop_str = []
                if props & 0x02: prop_str.append("READ")
                if props & 0x04: prop_str.append("WRITE_NO_RESP")
                if props & 0x08: prop_str.append("WRITE")
                if props & 0x10: prop_str.append("NOTIFY")
                if props & 0x20: prop_str.append("INDICATE")
                uuid_bytes = item[5:]
                uuid_hex = uuid_bytes[::-1].hex() if len(uuid_bytes) == 16 else uuid_bytes.hex()
                print(f"  [{i}] decl=0x{decl_handle:04x} val=0x{val_handle:04x} "
                      f"props={props:#04x}({','.join(prop_str)}) uuid={uuid_hex}")