import json
import time
from datetime import datetime, timezone

def xor_decode_buffer(buffer: str, key: int) -> bytes:
    """
    Decodes a hex-encoded buffer using XOR with the given key.

    Args:
        buffer (str): The hex-encoded buffer as a string.
        key (int): The XOR key to decode the buffer.

    Returns:
        bytes: The XOR-decoded bytes.
    """
    buffer_bytes = bytes.fromhex(buffer)
    decoded_bytes = bytes(b ^ key for b in buffer_bytes)
    return decoded_bytes

def create_json_from_decoded(decoded_bytes: bytes) -> dict:
    """
    Parses the decoded bytes and creates a JSON object.

    Args:
        decoded_bytes (bytes): The XOR-decoded bytes.

    Returns:
        dict: A JSON object containing the parsed data.
    """
    # Step 1: Parse the fixed header
    header = decoded_bytes[:6]  # First 6 bytes are the fixed header
    message_type = decoded_bytes[6]  # Next byte is the message type (e.g., 5 for calendar, 6 for mail)

    # Step 2: Parse the date/time
    date_time_end = 6 + 16  # Date/time is 16 bytes long (YYYYMMDDTHHMMSS)
    date_time_str = decoded_bytes[7:date_time_end].decode("utf-8")  # Include the last second
    # Convert date_time to a Unix timestamp in milliseconds
    timestamp_ms = int(time.mktime(datetime.strptime(date_time_str, "%Y%m%dT%H%M%S").timetuple()) * 1000)

    # Step 3: Parse ASCII strings with lengths
    strings = []
    index = date_time_end
    while index < len(decoded_bytes):
        # Read the length (1 byte, ignore the second byte)
        length = decoded_bytes[index]
        index += 2  # Skip 2 bytes (length prefix)

        # Read the string of the given length
        string = decoded_bytes[index:index+length].decode("utf-8", errors="ignore")
        strings.append(string)
        index += length

    # Step 4: Extract source, recipient, and split the fourth string into subject and body
    source = strings[0] if len(strings) > 0 else ""
    sender = strings[1] if len(strings) > 1 else ""
    subject = ""
    body = ""
    if len(strings) > 3:  # Ensure there is a fourth string
        fourth_string = strings[3]  # Get the fourth string
        if "\n" in fourth_string:
            subject, body = fourth_string.split("\n", 1)  # Split into subject and body at the first \n
        else:
            subject = fourth_string  # If no \n, treat the entire string as the subject

    # Step 5: Construct the JSON object
    json_object = {
        "header": header.hex(),
        "message_type": message_type,
        "timestamp_ms": timestamp_ms,
        "source": source,
        "sender": sender,
        "subject": subject,
        "body": body,
    }

    return json_object

# encode
def xor_encode_buffer(decoded_bytes: bytes, key: int) -> str:
    """
    Encodes a buffer using XOR with the given key.

    Args:
        decoded_bytes (bytes): The original decoded bytes to encode.
        key (int): The XOR key to encode the buffer.

    Returns:
        str: The XOR-encoded buffer as a hex string.
    """
    encoded_bytes = bytes(b ^ key for b in decoded_bytes)
    return encoded_bytes.hex()

def create_decoded_from_json(json_object: dict, key: int) -> str:
    """
    Creates an encoded buffer from a JSON object by reversing the decoding process.

    Args:
        json_object (dict): The JSON object containing the parsed data.
        key (int): The XOR key to encode the buffer.

    Returns:
        str: The XOR-encoded buffer as a hex string.
    """
    # Step 1: Reconstruct the fixed header
    header = bytes.fromhex(json_object["header"])

    # Step 2: Add the message type
    message_type = json_object["message_type"].to_bytes(1, "big")

    # Step 3: Add the date/time in the original format (YYYYMMDDTHHMMSS)
    timestamp_ms = json_object["timestamp_ms"]
    date_time = datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=timezone.utc).strftime("%Y%m%dT%H%M%S")
    date_time_bytes = date_time.encode("utf-8")

    # Step 4: Add the ASCII strings with lengths
    source = json_object["source"]
    sender = json_object["sender"]
    subject = json_object["subject"]
    body = json_object["body"]

    # Combine source, recipient, and strings
    all_strings = [
        source,
        sender,
        "",  # There is a 0-length string after sender, not sure what it is supposed to hold.
        f"{subject}\n{body}"  # Combine subject and body with a newline
    ]

    encoded_strings = b""
    for string in all_strings:
        length = len(string)
        encoded_strings += length.to_bytes(1, "big") + b"\x00"  # Add length (1 byte) and padding (1 byte)
        encoded_strings += string.encode("utf-8")

    # Step 5: Combine all parts into a single buffer
    decoded_bytes = header + message_type + date_time_bytes + encoded_strings

    # Step 6: Encode the buffer using XOR
    encoded_buffer = xor_encode_buffer(decoded_bytes, key)
    return encoded_buffer


#         0123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789
#         0         1         2         3         4         5         6         7         8
bufferGmail = "fffffffffffef9cdcfcdcacfcaceceabcfc8cbcccecffaffb8929e9693fdff929affff05ffab97968cdf968cdf9edf899a8d86df93909198df8c8a9d959a9c8bd1dfb29e86899adf9a899a91df8b9090df93909198d1dfbd8a8bdf979a8d9adf968bdf968cd1d1d1f5a8979e8bdf968cdf968bc0f5b6df8b97969194df889adf9c9e91df9b90df9d9a8b8b9a8ddf8b979e91df8b979adf909999969c969e93dfbc9e8c9690dfb8d2ac97909c94dfbe8f8fdedfab97968cdf9e8f8fdf8f8d9089969b9a8cdf8b979adf999093939088969198df9a878b8d9edf999a9e8b8a8d9a8cc5f5ac9a8b8cdf889e8b9c97d88cdf8d9a9296919b"
bufferGmail2 = "fcfffffffffff9cdcfcdcacfcaceceabcecccbcecac8faffb8929e9693f7ff929ad3dfb29e9693ffff05ffac8a9d959a9c8bc5df929a8c8c9e989adf8b90df929adf9e919bdf958a8c8b99908d8f908c8b969198cbc6bf98929e9693d19c9092f5be9b9b8d9a8c8cdf91908bdf99908a919bf5a6908a8ddf929a8c8c9e989adf889e8c91d88bdf9b9a9396899a8d9a9bdf8b90df958a8c8b99908d8f908c8b969198cbc6bf98929e9693d19c9092df9d9a9c9e8a8c9adf8b979adf9e9b9b8d9a8c8cdf9c908a939b91d88bdf9d9adf99908a919bd3df908ddf968cdf8a919e9d939adf8b90df8d9a9c9a96899adf929e9693d1f5b3ba"
bufferGmail3 = "fffffffffffff9cdcfcdcacfcaceceabcfc6cac7ccc9faffb8929e9693f5ffbe9396ba878f8d9a8c8cffff07ffb79e9bdf86908a8ddf9a869adf9091df8b97968cc0f5f5ab9e949adf9e91908b979a8ddf93909094df9e8bc5dfab9a9a919e989adfb29a91d88cdfb58a9196908ddfb7969897dfac9c97909093dfac8b8a9b9a918bdfb99e8c979690d1d1d1f51d7f733d5f1d7f733d5f1d7f733d5f1d7f733d5f1d7f733d5f1d7f733d5f1d7f733d5f1d7f733d5f1d7f733d5f1d7f733d5f1d7f733d5f1d7f733d5f1d7f733d5f3d5f1d7f733d5f1d7f733d5f1d7f733d5f1d7f733d5f1d7f733d5f1d7f733d5f1d7f733d5f1d7f73"
x =            "fbfffffffffef9cdcfcdcacfcaceceabcec8cbcccecafaffb8929e9693f3ffa6899a8b8b9adfa89093999affffddffac8a9d959a9c8bc5df8b9a8c8bdf998d9092dfa6899a8b8b9af5ab8d8c8bab8d8c8b"
bufferGmail4 = "fbfffffffffef9cdcfcdcacfcaceceabcecccbcccecafaffb8929e9693f3ffa6899a8b8b9adfa89093999affffddffac8a9d959a9c8bc5df8b9a8c8bdf998d9092dfa6899a8b8b9af5ab8d8c8bab8d8c8b"

bufferCal =   "fffffffffffefacdcfcdcacfcacfc9abcfc6cecccdc8f7ffbc9e939a919b9e8dedff1d7f711d7f55ab9a8c8bdfcc1d7f531d7f71ffffe2ff1d7f711d7f55c6c5cecadf1d7f6cdfcecfc5cecadfbeb21d7f531d7f71"
bufferHealth = "050000ffffffff000000000000000000dafafadcfa0ff77f7f7f7f7f7f7f7f7f000000ffffffff000000000000000000dafafadcff0ff77f7f7f7f7f7f7f7f7f000000ffffffff000000000000000000dafafaddaa0ff77f7f7f7f7f7f7f7f7f000000ffffffff000000000000000000dafafaddaf0ff77f7f7f7f7f7f7f7f7f000000ffffffff000000000000000000dafafaddba0ff77f7f7f7f7f7f7f7f7f000000ffffffff000000000000000000dafafaddbf0ff77f7f7f7f7f7f7f7f7f000000ffffffff000000000000000000dafafaddca0ff77f7f7f7f7f7f7f7f7f000000ffffffff000000000000000000dafafaddcf0ff7"

bufferEncoded = "fffffffffffef9cdcfcdcacfcacfc7abcdcfcac7ccc9faffb8929e9693fdff929af8ff8b9a8c8bdfcecfe6ff8c8a9d959a9c8bdf9396919af59d909b86df9c90918b9a918b"
# Decode with key 255
key = 255

decoded = xor_decode_buffer(bufferGmail4, key)
decoded_json = create_json_from_decoded(decoded)

print("Decoded JSON:")
print(json.dumps(decoded_json, indent=4))


# # Encode the buffer
key = 255
encoded_buffer = create_decoded_from_json(decoded_json, key)
print(f"Encoded Buffer: {encoded_buffer}")

# Decode the buffer back to verify
decoded_bytes = xor_decode_buffer(encoded_buffer, key)
decoded_json = create_json_from_decoded(decoded_bytes)
print("Decoded JSON:")
print(json.dumps(decoded_json, indent=4))

def xor_decode(buffer: str, key: int):
    buffer_bytes = bytes.fromhex(buffer)
    decoded = bytes(b ^ key for b in buffer_bytes)
    return decoded.decode("utf-8", errors="ignore")

# for key in range(256):
#     try:
#         result = xor_decode(bufferHealth, key)
#         # if "Test 3" in result:
#         print(f"Key {key}: {result}\n\n")
#     except Exception:
#         continue

