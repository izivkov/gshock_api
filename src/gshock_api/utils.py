from collections.abc import Sequence
import string
import time
from typing import Final

# Constant for the prefix "0x"
hex_prefix: Final[str] = "0x"
# Constant for the null character used in trimming
null_char: Final[str] = "\0"


def to_casio_cmd(bytes_str: str) -> bytes:
    """
    Converts a compact hexadecimal string (e.g., 'A3010C') into a bytes object.
    """
    # Split the string into two-character parts ('A3', '01', '0C')
    parts: list[str] = [bytes_str[i: i + 2] for i in range(0, len(bytes_str), 2)]
    
    # Convert each part to an integer from base 16
    hex_arr: list[int] = [int(s, 16) for s in parts]
    
    # Return the final bytes object
    return bytes(hex_arr)


def to_int_array(hex_str: str) -> list[int]:
    """
    Converts a space-separated hexadecimal string (e.g., '0xA3 0x01 0x0C') into an array of integers.
    """
    int_arr: list[int] = []
    str_array: list[str] = hex_str.split(" ")
    
    for s in str_array:
        # Use remove_prefix for clean constant usage
        if s.startswith(hex_prefix):
            s = remove_prefix(s, hex_prefix)
            
        # Ensure the string is not empty before converting
        if s:
            int_arr.append(int(s, 16))
            
    return int_arr


def to_compact_string(hex_str: str) -> str:
    """
    Removes spaces and optional '0x' prefixes from a hex string (e.g., '0x01 0x2A' -> '012A').
    """
    compact_string: str = ""
    str_array: list[str] = hex_str.split(" ")
    
    for s in str_array:
        # Remove "0x" prefix if present
        if s.startswith(hex_prefix):
            s = remove_prefix(s, hex_prefix)
            
        compact_string += s

    return compact_string


def to_hex_string(byte_arr: bytes | bytearray | Sequence[int]) -> str:
    """
    Converts a bytes-like object or sequence of integers into a space-separated 
    hexadecimal string with '0x' prefix (e.g., b'\x01\x2A' -> '0x01 2A').
    """
    hex_parts: str = " ".join(format(x, "02X") for x in byte_arr)
    return f"{hex_prefix}{hex_parts}"


def remove_prefix(input_string: str, prefix: str) -> str:
    """
    Removes a prefix string from the start of the input string if it exists.
    """
    return input_string[len(prefix):] if input_string.startswith(prefix) else input_string


def to_ascii_string(hex_str: str, command_length_to_skip: int) -> str:
    """
    Converts a hex string containing ASCII characters into an ASCII string, 
    skipping a specified number of leading hex bytes (the command).
    """
    str_array_with_command: list[str]
    
    if " " not in hex_str and len(hex_str) % 2 == 0:
        # Handle compact hex strings (no spaces)
        str_array_with_command = [hex_str[i: i + 2] for i in range(0, len(hex_str), 2)]
    else:
        # Handle space-separated hex strings
        str_array_with_command = hex_str.split(" ")
    
    # Skip the command part (each element is one byte)
    str_array: list[str] = str_array_with_command[command_length_to_skip:]
    
    asc: str = "".join(str_array)
    return bytes.fromhex(asc).decode("ASCII")


def trim_non_ascii_characters(input_string: str) -> str:
    """
    Removes the null character ('\0') used for padding from a string.
    """
    return input_string.replace(null_char, "")


def current_milli_time() -> int:
    """
    Returns the current time in milliseconds since the epoch as an integer.
    """
    return round(time.time() * 1000)


def clean_str(dirty_str: str) -> str:
    """
    Removes non-printable ASCII characters from a string.
    """
    printable: set[str] = set(string.printable)
    return "".join(filter(lambda x: x in printable, dirty_str))


def to_byte_array(input_string: str, max_len: int) -> bytearray:
    """
    Converts a string to a bytearray, padding it with null bytes if shorter 
    than max_len or truncating if longer.
    """
    ret_arr: bytearray = bytearray(input_string.encode("utf-8"))
    current_len: int = len(ret_arr)
    
    if current_len > max_len:
        # Truncate
        return ret_arr[:max_len]
    if current_len < max_len:
        # Pad with null bytes
        return ret_arr + bytearray(max_len - current_len)
        
    return ret_arr


def to_hex_string_compact(ascii_str: str, max_len: int) -> str:
    """
    Converts an ASCII string to a compact hexadecimal string (e.g., 'TEST' -> '54455354').
    """
    byte_arr: bytearray = bytearray(ascii_str, "ascii")
    hex_str: str = ""
    
    for byte in byte_arr:
        hex_str += f"{byte:02x}"
        
    return hex_str


def dec_to_hex(dec: int) -> int:
    """
    Converts a decimal integer to a hexadecimal integer value.
    Note: This function returns an int derived from hex string, which effectively is equal to the input.
    """
    return int(str(hex(dec))[2:])


def encode_string(ascii_string: str, max_len: int) -> str:
    """
    Encodes an ASCII string into a padded, compact hexadecimal string.
    """
    int_arr: list[int] = [ord(c) for c in ascii_string]

    while len(int_arr) < max_len:
        int_arr.append(0)

    hex_string: str = "".join(f"{i:02X}" for i in int_arr)

    return hex_string
