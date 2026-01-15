import logging
import os
import sys

# Add src to path so we can import gshock_api
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gshock_api.logger import logger

from dataclasses import dataclass

@dataclass
class HealthData:
    timestamp: int  # Epoch timestamp
    steps: int
    calories: int
    distance: int = 0
    heart_rate_avg: int = 0
    heart_rate_max: int = 0
    heart_rate_min: int = 0
    # Additional fields can be added as needed

@dataclass
class DailyHealthData:
    date: str  # YYYY-MM-DD
    snapshots: list[HealthData]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

def xor_decode(data: bytes, key: int = 255) -> bytes:
    return bytes([b ^ key for b in data])

def decode_health_data(decoded: bytes, buffer_name: str = "") -> DailyHealthData | None:
    try:
        logger.info(f"\n{'='*60}")
        logger.info(f"Decoding {buffer_name}")
        logger.info(f"Raw decoded hex: {decoded.hex()}")
        logger.info(f"Length: {len(decoded)} bytes")
        
        if len(decoded) < 22:
            logger.info(f"Decoded data too short to parse")
            return None
        
        # Parse date from offsets 5-7
        year = decoded[5] + 2000
        month = decoded[6]
        day = decoded[7]
        logger.info(f"\nDate: {year}-{month:02d}-{day:02d}")
        
        # Steps found at offset 15-16
        steps = int.from_bytes(decoded[15:17], 'little')
        logger.info(f"Steps at offset 15-16: {steps}")
        
        # Search for calories around the steps location
        logger.info(f"\nSearching for calories (1780 = 0x06F4):")
        
        # Check common patterns
        for offset in range(10, min(30, len(decoded)-1)):
            val = int.from_bytes(decoded[offset:offset+2], 'little')
            # Check if value is in reasonable calorie range
            if 500 <= val <= 3000:
                logger.info(f"  Offset {offset}: {val}")
        
        # Let me also check if calories might be encoded differently
        # 1780 calories... let me check surrounding bytes
        logger.info(f"\nBytes around steps location:")
        for i in range(10, 25):
            if i < len(decoded):
                logger.info(f"  Offset {i}: 0x{decoded[i]:02x} ({decoded[i]}) = "
                          f"LE-16bit: {int.from_bytes(decoded[i:i+2], 'little') if i+1 < len(decoded) else 'N/A'}")
        
        # Try offset 19-20 based on your original code
        calories_19_20 = int.from_bytes(decoded[19:21], 'little') if len(decoded) > 20 else 0
        logger.info(f"\nOriginal offset 19-20 for calories: {calories_19_20}")
        
        # Actually, let me check if 1780 appears ANYWHERE in the buffer
        logger.info(f"\nSearching entire buffer for 1780 (0xF4 0x06 in LE):")
        for i in range(len(decoded) - 1):
            if decoded[i] == 0xF4 and decoded[i+1] == 0x06:
                logger.info(f"*** FOUND 1780 at offset {i}: 0x{decoded[i]:02x} 0x{decoded[i+1]:02x}")
        
        # Also search for it in big endian (0x06 0xF4)
        logger.info(f"\nSearching for 1780 in big endian (0x06 0xF4):")
        for i in range(len(decoded) - 1):
            if decoded[i] == 0x06 and decoded[i+1] == 0xF4:
                val = int.from_bytes(decoded[i:i+2], 'big')
                logger.info(f"*** FOUND {val} at offset {i}: 0x{decoded[i]:02x} 0x{decoded[i+1]:02x}")
        
        return None
        
    except Exception as e:
        logger.error(f"Error parsing health data: {e}")
        import traceback
        traceback.print_exc()
        return None
# Update your test function:
def run_hardcoded_test():
    logger.info("Starting Hardcoded Health Parser Test...")
    
    test_buffers = [
        ("Buffer 1 - Jan 7 Live (Steps 0, Cal 702)", 
         "05FFF0FFFFFFE5FEF8F1DFC9BAFFFFFFFFFFFF41FDEF7B"),
        ("Buffer 2 - Jan 6 History (Steps 1268, Cal 1780)",
         "059C8DFFFFFFD9FEF813A2D185FCFFA30BFBFFFFBFE0FFFFF0FF9FFFFFFFFF9DFFFFFFFFF0F0FFFFD8FFFFFFFFFEC9EFDAFEFFEECF009E010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101FF00A157FFCFFFC8FF9B00007E2B"),
    ]
    
    for name, buffer in test_buffers:
        data = bytearray.fromhex(buffer)
        if len(data) > 1:
            payload = data[1:]
            decoded_data = xor_decode(payload, key=255)
            decode_health_data(decoded_data, name)
            
if __name__ == "__main__":
    run_hardcoded_test()
