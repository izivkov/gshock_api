import json
import difflib
from datetime import datetime, timezone
from gshock_api.app_notification import EmailSmsNotification, CalendarNotification

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

key = 255

def compare_strings(string1: str, string2: str) -> None:
    """
    Compares two strings and displays their differences in a compact format.

    Args:
        string1 (str): The first string to compare.
        string2 (str): The second string to compare.

    Returns:
        None
    """
    # Use difflib to generate a side-by-side comparison
    diff = difflib.ndiff(string1, string2)
    differences = []
    for line in diff:
        if line.startswith("- ") or line.startswith("+ "):  # Only include differences
            differences.append(line)

    # Group differences into a compact format
    print("Differences between the strings:")
    for diff_line in differences:
        print(diff_line)

############################################################
# EMAIL & SMS
############################################################
def extract_strings_from_sms_buffer(decoded_bytes: bytes) -> dict:
    """
    Extracts strings from an SMS buffer and returns them as a dictionary.

    Args:
        decoded_bytes (bytes): The XOR-decoded bytes of the SMS buffer.

    Returns:
        dict: A dictionary containing the extracted fields (date, source app, sender, and message).
    """
    index = 0

    # Step 1: Parse the header (first 7 bytes)
    header = decoded_bytes[:7].decode("utf-8", errors="ignore")
    message_type = decoded_bytes[6]  # Next byte is the message type (e.g., 5 for calendar, 6 for mail)

    index += 7

    # Step 2: Parse the date (15 bytes)
    date_time = decoded_bytes[index:index + 15].decode("utf-8", errors="ignore")
    index += 15

    # Step 3: Parse the source app
    source_length = decoded_bytes[index]  # Length of the source app
    index += 1  # Move past the length byte
    index += 1  # Skip the padding byte (00)
    source_app = decoded_bytes[index:index + source_length].decode("utf-8", errors="ignore")
    index += source_length

    # Step 4: Parse the sender phone number
    sender_length = decoded_bytes[index]  # Length of the sender phone number
    index += 1  # Move past the length byte
    index += 1  # Skip the padding byte (00)
    sender = decoded_bytes[index:index + sender_length].decode("utf-8", errors="ignore")
    index += sender_length

    # Step 5: Skip the fixed padding (00 00)
    index += 2

    # Step 6: Parse the message
    message_length = decoded_bytes[index]  # Length of the message
    index += 1  # Move past the length byte
    index += 1  # Skip the padding byte (00)
    message = decoded_bytes[index:index + message_length].decode("utf-8", errors="ignore")

    # Construct the result dictionary
    sms_data = {
        "message_type": message_type,
        "date_time": date_time,
        "source_app": source_app,
        "sender": sender,
        "message": message,
    }

    return sms_data

def create_sms_buffer_from_object(sms_object: dict, expected_buffer: bytes = None) -> bytes:
    """
    Creates an SMS buffer from a dictionary object and optionally compares it with an expected buffer.

    Args:
        sms_object (dict): The dictionary containing the SMS data.
        expected_buffer (bytes, optional): The expected buffer to compare against.

    Returns:
        bytes: The reconstructed SMS buffer as bytes.

    Raises:
        ValueError: If the constructed buffer does not match the expected buffer at any step.
    """
    def compare_partial_buffer(partial_buffer: bytes, step_name: str):
        """Compares the partial buffer with the expected buffer."""
        if expected_buffer is not None:
            if not expected_buffer.startswith(partial_buffer):
                # Find the first mismatch
                for i, (expected_byte, actual_byte) in enumerate(zip(expected_buffer, partial_buffer)):
                    if expected_byte != actual_byte:
                        raise ValueError(
                            f"Mismatch at step '{step_name}':\n"
                            f"Location: Byte {i}\n"
                            f"Expected: {expected_byte:02x}\n"
                            f"Actual:   {actual_byte:02x}\n"
                            f"Expected Buffer: {expected_buffer[:len(partial_buffer)].hex()}\n"
                            f"Actual Buffer:   {partial_buffer.hex()}"
                        )

    # Step 1: Header
    header = sms_object["header"].encode("utf-8")
    compare_partial_buffer(header, "header")

    # Step 2: Date-Time
    date_time = sms_object["date_time"].encode("utf-8")
    partial_buffer = header + date_time
    compare_partial_buffer(partial_buffer, "date_time")

    # Step 3: Source App
    source_app = sms_object["source_app"]
    source_length = len(source_app)
    source_bytes = source_length.to_bytes(1, "big") + b"\x00" + source_app.encode("utf-8")
    partial_buffer += source_bytes
    compare_partial_buffer(partial_buffer, "source_app")

    # Step 4: Sender Phone Number
    sender = sms_object["sender"]
    sender_length = len(sender)
    sender_bytes = sender_length.to_bytes(1, "big") + b"\x00" + sender.encode("utf-8")
    partial_buffer += sender_bytes
    compare_partial_buffer(partial_buffer, "sender")

    # Step 5: Message
    message = sms_object["message"]
    print(f"message: {message}")
    message_length = len(message)
    message_bytes = message_length.to_bytes(1, "big") + b"\x00" + message.encode("utf-8")
    partial_buffer += b"\x00\x00" + message_bytes
    compare_partial_buffer(partial_buffer, "message")

    # Return the final buffer
    return partial_buffer

bufferSMS = "fdfffffffffef9cdcfcdcacfcaceccabcec7cfcdcdcef7ffb29a8c8c9e989a8cf1ffd7cbcec9d6dfc7ccccd2cdcfc8c7ffffe6ffab97968cdf968cdf9edf8c96928f939adf929a8c8c9e989adf"
bufferSMS_2 ="fcfffffffffef9cdcfcdcacfcaceccabcec7cfcdcac6f7ffb29a8c8c9e989a8cf1ffd7cbcec9d6dfc7ccccd2cdcfc8c7fffff4ffbe91908b979a8ddf90919a"
bufferGmail = "fffffffffffef9cdcfcdcacfcaceceabcfc8cbcccecffaffb8929e9693fdff929affff05ffab97968cdf968cdf9edf899a8d86df93909198df8c8a9d959a9c8bd1dfb29e86899adf9a899a91df8b9090df93909198d1dfbd8a8bdf979a8d9adf968bdf968cd1d1d1f5a8979e8bdf968cdf968bc0f5b6df8b97969194df889adf9c9e91df9b90df9d9a8b8b9a8ddf8b979e91df8b979adf909999969c969e93dfbc9e8c9690dfb8d2ac97909c94dfbe8f8fdedfab97968cdf9e8f8fdf8f8d9089969b9a8cdf8b979adf999093939088969198df9a878b8d9edf999a9e8b8a8d9a8cc5f5ac9a8b8cdf889e8b9c97d88cdf8d9a9296919b"

# decoded_bytes = xor_decode_buffer(bufferGmail, key)

# sms_object = extract_strings_from_sms_buffer(decoded_bytes)
# print("Decoded SMS JSON:")
# print(json.dumps(sms_object, indent=4))

# print("======================== END of SMS ========================")

############################################################
# CLAENDAR
############################################################

def create_calendar_json_from_decoded(decoded_bytes: bytes) -> dict:
    """
    Parses the decoded bytes and creates a JSON object for a calendar event.

    Args:
        decoded_bytes (bytes): The XOR-decoded bytes.

    Returns:
        dict: A JSON object containing the calendar event data.
    """
    # Step 1: Parse the header
    header_end = 7  # The header is 7 bytes long
    header = decoded_bytes[:header_end].hex()  # Convert the header to a hex string

    # Step 2: Parse the date_time
    date_time_end = header_end + 15  # The date_time is 15 bytes long (YYYYMMDDTHHMMSS)
    date_time = decoded_bytes[header_end:date_time_end].decode("utf-8")

    # Step 3: Parse the source
    source_length = decoded_bytes[date_time_end]  # First byte holds the length
    source_start = date_time_end + 2  # Skip the 2-byte length field
    source_end = source_start + source_length
    source_app = decoded_bytes[source_start:source_end].decode("utf-8", errors="ignore")

    # Step 4: Parse the title
    title_length = decoded_bytes[source_end] - 12 # First byte holds the length, subtract 12 for some reason
    title_start = source_end + 8 # skip [1d][00][e2][80][8e][e2][80][aa]
    title_end = title_start + title_length
    title = decoded_bytes[title_start:title_end].decode("utf-8", errors="ignore")

    # Step 5: Skip fixed separators
    index = title_end
    index += 15

    # Step 9: Construct the JSON object
    calendar_event = {
        "date_time": date_time,
        "source_app": source_app,
        "title": title,
        "start_time": start_time,
        "end_time": end_time,
    }

    return calendar_event

def extract_strings_from_buffer(decoded_bytes: bytes) -> list:
    """
    Extracts strings from the decoded bytes until the end of the buffer.
    Strings are separated by the [e2][80] marker, and empty strings are included for gaps.

    Args:
        decoded_bytes (bytes): The XOR-decoded bytes.

    Returns:
        list: A list of strings extracted from the buffer.
    """
    strings = []
    index = 0

    # First handle timestamt and source
    header_end = 7  # The header is 7 bytes long
    header = decoded_bytes[:header_end].hex()  # Convert the header to a hex string

    # Step 2: Parse the date_time
    date_time_end = header_end + 15  # The date_time is 15 bytes long (YYYYMMDDTHHMMSS)
    date_time = decoded_bytes[header_end:date_time_end].decode("utf-8")
    strings.append(date_time.strip())

    # Step 3: Parse the source
    source_length = decoded_bytes[date_time_end]  # First byte holds the length
    source_start = date_time_end + 2  # Skip the 2-byte length field
    source_end = source_start + source_length
    source = decoded_bytes[source_start:source_end].decode("utf-8", errors="ignore")
    strings.append(source.strip())

    index = source_end + 2  # Skip the 2-byte length field

    # The rest of the buffer is strings separated by [e2][80]
    while index < len(decoded_bytes):
        # Find the start of the string
        string_start = index

        # Look for the [e2][80] marker to find the end of the string
        while index < len(decoded_bytes) - 1:
            if decoded_bytes[index] == 0xe2 and decoded_bytes[index + 1] == 0x80:
                break
            index += 1

        # Extract the string
        string_end = index
        string = decoded_bytes[string_start:string_end].decode("utf-8", errors="ignore")
        strings.append(string.strip())

        # Skip the [e2][80] marker
        index += 2

    return strings

from datetime import datetime

from datetime import datetime

def create_calendar_json_from_strings(strings: list) -> dict:
    """
    Creates a JSON object for a calendar event from an array of strings.

    Args:
        strings (list): The array of strings extracted from the buffer.

    Returns:
        dict: A JSON object containing the calendar event data.
    """
    if len(strings) < 10:
        raise ValueError("Insufficient data in the strings array to create a calendar event JSON.")

    # Extract and process fields
    date_time_str = strings[0]  # First string is the date_time
    date_time = date_time_str
    source = strings[1]  # Second string is the source
    title = strings[4]  # Fifth string is the title
    start_time = strings[8]  # Ninth string is the start time
    end_time = strings[9]  # Tenth string is the end time

    # Construct the JSON object
    calendar_event = {
        "type": "5",
        "date_time": date_time,
        "source_app": source,
        "title": title,
        "start_time": start_time,
        "end_time": end_time,
    }

    return calendar_event

def create_decoded_buffer_from_json(json_object: dict) -> bytes:
    """
    Creates a decoded buffer from a JSON object.

    Args:
        json_object (dict): The JSON object containing the calendar event data.

    Returns:
        bytes: The decoded buffer as bytes.
    """
    # Step 1: Fixed header
    header = bytes.fromhex("08000000000105")  # Corrected header


    # Step 2: Date-time
    date_time_str = json_object["date_time"]
    date_time_bytes = date_time_str.encode("utf-8")

    # Step 3: Source
    source = json_object["source_app"]
    source_length = len(source)
    source_bytes = source_length.to_bytes(1, "big") + b"\x00" + source.encode("utf-8")

    # Step 4: Title
    title = json_object["title"]
    title_separator = b"\x1d\x00\xe2\x80\x8e\xe2\x80\xaa"  # Separator before the title
    title_bytes = title_separator + title.encode("utf-8")

    # Step 5: Start time and end time
    start_time = json_object["start_time"]
    end_time = json_object["end_time"]
    time_separator = b"\xe2\x80\xac\xe2\x80\x8e\x00\x00\x1e\x00\xe2\x80\x8e\xe2\x80\xaa"  # Separator before times
    start_time_bytes = start_time.encode("utf-8")
    end_time_separator = b"\xe2\x80\x93"  # Separator between start and end times
    end_time_bytes = end_time.encode("utf-8")

    # Add the missing sequence after "280aa31303a3430"
    additional_sequence = b"\x20\xe2\x80\x93\x20" + end_time_bytes + b"\xe2\x80\xac\xe2\x80\x8e"

    # Combine start and end times
    time_bytes = time_separator + start_time_bytes + additional_sequence

    # Step 6: Combine all parts
    decoded_buffer = header + date_time_bytes + source_bytes + title_bytes + time_bytes
    return decoded_buffer

result =          "f7fffffffffefacdcfcdcacfcaceceabcdcdcecfcfcff7ffbc9e939a919b9e8de2ff1d7f711d7f55b0919ad28b96929a1d7f531d7f71ffffe1ff1d7f711d7f55cecfc5cbcfdf1d7f6cdfcecec5cbcfdfafb21d7f531d7f71"  
bufferCalendar =  "f7fffffffffefacdcfcdcacfcaceceabcdcdcecfcfcff7ffbc9e939a919b9e8debff1d7f711d7f55b0919ad28b96929a1d7f531d7f71ffffe1ff1d7f711d7f55cecfc5cbcfdf1d7f6cdfcecec5cbcfdfafb21d7f531d7f71"

res1 =            "f9fffffffffefacdcfcdcacfcaceceabcdcdcfc6cfcbf7ffbc9e939a919b9e8ddaff1d7f711d7f55b290919b9e86dfba899a8d86df889a9a94df99908d9a899a8d1d7f531d7f71ffffe1ff1d7f711d7f55cecfc5cccfdf1d7f6cdfcecec5cccfdfafb21d7f531d7f71"
bufferCalendar2 = "f9fffffffffefacdcfcdcacfcaceceabcdcdcfc6cfcbf7ffbc9e939a919b9e8ddaff1d7f711d7f55b290919b9e86dfba899a8d86df889a9a94df99908d9a899a8d1d7f531d7f71ffffe1ff1d7f711d7f55cecfc5cccfdf1d7f6cdfcecec5cccfdfafb21d7f531d7f71"

a =               "fafffffffffefacdcfcdcacfcaceceabcdcdcfcccac7f7ffbc9e939a919b9e8de2ff1d7f711d7f55be918a9e939386df9691dfb29e86dfcece1d7f531d7f71ffffe1ff1d7f711d7f55cecfc5cecadf1d7f6cdfcecec5cecadfafb21d7f531d7f71"

b = "[05][00][00][00][00][01][05]20250511T220358[08][00]Calendar[1d][00][e2][80][8e][e2][80][aa]Anually in May 11[e2][80][ac][e2][80][8e][00][00][1e][00][e2][80][8e][e2][80][aa]10:15 [e2][80][93] 11:15 PM[e2][80][ac][e2][80][8e]"

decoded_bytes = xor_decode_buffer(bufferCalendar, key)
# print(f"Decoded CAL Bytes: {decoded_bytes.hex()}")
# Extract strings from the buffer
strings = extract_strings_from_buffer(decoded_bytes)

cal_object = create_calendar_json_from_strings(strings)
print("Calendar JSON:")
print(json.dumps(cal_object, indent=4))

# cal_object = CalendarNotification(
#     date_time="20231001T120000",
#     source_app="CalendarApp",
#     title="Meeting with Team",
#     start_time="9:45 10:15 PM",
#     end_time="10:45"
# )

decoded_buffer = create_decoded_buffer_from_json(cal_object)
print(f"Decoded Buffer: {decoded_buffer.hex()}")

# Replace undecodable characters with their hex representation in square brackets
decoded_str = ''.join(
    chr(b) if 32 <= b <= 126 else f"[{b:02x}]" for b in decoded_buffer
)
print(f"Calender decoded_str:\n{decoded_str}\n\n")

encoded_buffer = xor_encode_buffer(decoded_buffer, key)
print(f"Encoded Buffer: {encoded_buffer}")
print(f"Orig    Buffer: {bufferCalendar}")

print (f"Result: {res1 == bufferCalendar}")

"08000000000105323032353035313154323231303030080043616c656e6461721400e2808ee280aa4f6e652d74696d65e280ace2808e00001e00e2808ee280aa31303a343020e280932031313a343020504de280ace2808e"
"08000000000105323032353035313154323231303030080043616c656e6461721d00e2808ee280aa4f6e652d74696d65e280ace2808e00001e00e2808ee280aa31303a343020e280932031313a343020504de280ace2808e"
# cal_object = create_calendar_json_from_decoded(decoded_bytes)
# print("Decoded Calendar JSON:")
# print(json.dumps(cal_object, indent=4))


