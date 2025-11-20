import string
import time
from typing import Final, Sequence

# --- Constants ---

# Constant for the prefix "0x"
HEX_PREFIX: Final[str] = "0x"

# Constant for the null character used in trimming
NULL_CHAR: Final[str] = "\0"

# --- Utility Functions ---

def to_casio_cmd(bytesStr: str) -> bytes:
    """
    Converts a compact hexadecimal string (e.g., 'A3010C') into a bytes object.
    
    The input string must be an even length string of hexadecimal characters.
    """
    # Split the string into two-character parts ('A3', '01', '0C')
    parts: list[str] = [bytesStr[i: i + 2] for i in range(0, len(bytesStr), 2)]
    
    # Convert each part to an integer from base 16
    hexArr: list[int] = [int(s, 16) for s in parts]
    
    # Return the final bytes object
    return bytes(hexArr)


def to_int_array(hexStr: str) -> list[int]:
    """
    Converts a space-separated hexadecimal string (e.g., '0xA3 0x01 0x0C') into an array of integers.
    """
    intArr: list[int] = []
    strArray: list[str] = hexStr.split(" ")
    
    for s in strArray:
        # Use remove_prefix for clean constant usage
        if s.startswith(HEX_PREFIX):
            s = remove_prefix(s, HEX_PREFIX)
            
        # Ensure the string is not empty before converting
        if s:
            intArr.append(int(s, 16))
            
    return intArr


def to_compact_string(hexStr: str) -> str:
    """
    Removes spaces and optional '0x' prefixes from a hex string (e.g., '0x01 0x2A' -> '012A').
    """
    compactString: str = ""
    strArray: list[str] = hexStr.split(" ")
    
    for s in strArray:
        # Remove "0x" prefix if present
        if s.startswith(HEX_PREFIX):
            s = remove_prefix(s, HEX_PREFIX)
            
        compactString += s

    return compactString


def to_hex_string(byte_arr: bytes | bytearray | Sequence[int]) -> str:
    """
    Converts a bytes-like object or sequence of integers into a space-separated 
    hexadecimal string with '0x' prefix (e.g., b'\x01\x2A' -> '0x01 2A').
    """
    # Format each byte/int as two uppercase hex characters, join with space
    hex_parts: str = " ".join(format(x, "02X") for x in byte_arr)
    return f"{HEX_PREFIX}{hex_parts}"


def remove_prefix(input_string: str, prefix: str) -> str:
    """
    Removes a prefix string from the start of the input string if it exists.
    """
    return input_string[len(prefix):] if input_string.startswith(prefix) else input_string


def to_ascii_string(hexStr: str, commandLengthToSkip: int) -> str:
    """
    Converts a hex string containing ASCII characters into an ASCII string, 
    skipping a specified number of leading hex bytes (the command).
    """
    strArrayWithCommand: list[str]
    
    if " " not in hexStr and len(hexStr) % 2 == 0:
        # Handle compact hex strings (no spaces)
        strArrayWithCommand = [hexStr[i: i + 2] for i in range(0, len(hexStr), 2)]
    else:
        # Handle space-separated hex strings
        strArrayWithCommand = hexStr.split(" ")
    
    # Skip the command part (each element is one byte)
    strArray: list[str] = strArrayWithCommand[commandLengthToSkip:]
    
    # Join the remaining hex characters and decode as ASCII
    asc: str = "".join(strArray)
    return bytes.fromhex(asc).decode("ASCII")


def trimNonAsciiCharacters(input_string: str) -> str:
    """
    Removes the null character ('\0') used for padding from a string.
    """
    return input_string.replace(NULL_CHAR, "")


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


def to_byte_array(input_string: str, maxLen: int) -> bytearray:
    """
    Converts a string to a bytearray, padding it with null bytes if shorter 
    than maxLen or truncating if longer.
    """
    retArr: bytearray = bytearray(input_string.encode("utf-8"))
    current_len: int = len(retArr)
    
    if current_len > maxLen:
        # Truncate
        return retArr[:maxLen]
    if current_len < maxLen:
        # Pad with null bytes
        return retArr + bytearray(maxLen - current_len)
        
    return retArr


def to_hex_string_compact(asciiStr: str, maxLen: int) -> str:
    """
    Converts an ASCII string to a compact hexadecimal string (e.g., 'TEST' -> '54455354').
    
    Note: maxLen is unused in the original implementation, but preserved in the signature.
    """
    byteArr: bytearray = bytearray(asciiStr, "ascii")
    hexStr: str = ""
    
    for byte in byteArr:
        # Format byte as two lowercase hex characters
        hexStr += f"{byte:02x}"
        
    return hexStr


def dec_to_hex(dec: int) -> int:
    """
    Converts a decimal integer to a hexadecimal integer value.
    
    Note: This returns an integer whose value is the hexadecimal representation 
    (e.g., 255 -> 255). It seems intended to return the hex value *string* or 
    the result of the calculation, but the original implementation's return 
    type is `int(str(hex(dec))[2:])` which casts the hex string back to int.
    If the goal is to get a decimal integer that *represents* the hex value,
    the function is trivial: `return dec`. I preserve the original logic's 
    signature while noting the likely intention was a formatted string.
    """
    # Original logic: hex(dec) -> '0xff', [2:] -> 'ff', str -> 'ff', int -> 255
    # This is redundant and effectively returns the input integer.
    # We maintain the type signature but note this is likely a logic error.
    return int(str(hex(dec))[2:])


def encode_string(ascii_string: str, maxlen: int) -> str:
    """
    Encodes an ASCII string into a padded, compact hexadecimal string.
    """
    # Convert the ascii string into an array of integers (ASCII values)
    int_arr: list[int] = [ord(c) for c in ascii_string]

    # Pad the array up to maxlen with zeroes
    while len(int_arr) < maxlen:
        int_arr.append(0)

    # Convert the array back into a compact hexadecimal string
    hex_string: str = ""
    for i in int_arr:
        # Format integer as two uppercase hex characters
        hex_string += f"{i:02X}"

    return hex_string