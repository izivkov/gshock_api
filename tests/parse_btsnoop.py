
import datetime
import struct
import sys

# ANSI colors for log differentiation
COLORS = [
    "\033[91m", # Red
    "\033[92m", # Green
    "\033[93m", # Yellow
    "\033[94m", # Blue
    "\033[95m", # Magenta
    "\033[96m", # Cyan
    "\033[97m", # White
]
RESET_COLOR = "\033[0m"

def parse_btsnoop(filepath):
    with open(filepath, "rb") as f:
        # Header
        header = f.read(16)
        if not header.startswith(b"btsnoop\0"):
            print("Not a btsnoop file")
            return

        print("Parsing BTSnoop file...")
        
        packet_count = 0
        while True:
            # Record Header
            # Original Length (4), Included Length (4), Packet Flags (4), Cumulative Drops (4), Timestamp (8)
            rec_header = f.read(24)
            if len(rec_header) < 24:
                break
                
            orig_len, inc_len, flags, drops, ts = struct.unpack(">IIIIQ", rec_header)
            
            packet_data = f.read(inc_len)
            
            if len(packet_data) < 1:
                continue

            # H4 Packet Type
            pkt_type = packet_data[0]
            
            # 0x02 is ACL Data
            if pkt_type == 0x02:
                # ACL Header: Handle & Flags (2), Data Len (2)
                if len(packet_data) < 5:
                    continue
                
                handle_flags, data_len = struct.unpack("<HH", packet_data[1:5])
                handle = handle_flags & 0x0FFF
                pb_flag = (handle_flags >> 12) & 0x3
                bc_flag = (handle_flags >> 14) & 0x3
                
                # L2CAP Data
                l2cap_data = packet_data[5:]
                if len(l2cap_data) < 4:
                    continue
                
                l2cap_len, l2cap_cid = struct.unpack("<HH", l2cap_data[:4])
                payload = l2cap_data[4:]
                
                # CID 4 is Attribute Protocol (ATT)
                if l2cap_cid == 0x0004:
                    opcode = payload[0]
                    
                    # 0x12: Write Request, 0x52: Write Command, 0x1B: Notification
                    opcode_name = "Unknown"
                    att_handle = 0
                    att_value = b""
                    
                    if opcode == 0x52: # Write Command
                        opcode_name = "Write Cmd"
                        att_handle = struct.unpack("<H", payload[1:3])[0]
                        att_value = payload[3:]
                    elif opcode == 0x12: # Write Request
                        opcode_name = "Write Req"
                        att_handle = struct.unpack("<H", payload[1:3])[0]
                        att_value = payload[3:]
                    elif opcode == 0x1B: # Notification
                        opcode_name = "Notify"
                        att_handle = struct.unpack("<H", payload[1:3])[0]
                        att_value = payload[3:]    
                    elif opcode == 0x0A: # Read Response
                         opcode_name = "Read Rsp"
                         att_value = payload[1:]

                    if opcode_name != "Unknown":
                        # Convert timestamp (microseconds since 0001-01-01) to readable format
                        # 0x00dcddb30f2f8000 is the offset in microseconds to the Unix epoch (1970-01-01)
                        # Or simply use datetime arithmetic
                        dt = datetime.datetime(1, 1, 1) + datetime.timedelta(microseconds=ts)
                        dt_new = dt - datetime.timedelta(hours=5)
                        time_str = dt_new.strftime("%H:%M:%S.%f")
                        
                        # Select color based on handle to distinguish different characteristics
                        color = COLORS[att_handle % len(COLORS)]
                        print(f"{color}[{time_str}] #{packet_count} {opcode_name} Handle: 0x{att_handle:04X} Value: {att_value.hex().upper()}{RESET_COLOR}")
                    
            packet_count += 1

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 parse_btsnoop.py <file>")
    else:
        parse_btsnoop(sys.argv[1])
