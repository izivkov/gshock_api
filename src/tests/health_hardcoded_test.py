import logging
import os
import sys
from gshock_api.health_data import DailyHealthData, HealthData

# Add src to path so we can import gshock_api
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gshock_api.logger import logger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

def xor_decode(data: bytes, key: int = 255) -> bytes:
    return bytes([b ^ key for b in data])

def run_hardcoded_test():
    logger.info("Starting Hardcoded Health Parser Test (FINAL)...")

    test_buffers = [
        # 1. Jan 7 Live Update (Steps 0, Calories 702) - RAW
        "05FFF0FFFFFFE5FEF8F1DFC9BAFFFFFFFFFFFF41FDEF7B", 
        
        # 2. Jan 6 History Record (Steps 1268, Calories 1780) - RAW
        # This is a segment from a long buffer that contains: 26 01 07 ec ...
        "059C8DFFFFFFD9FEF813A2D185FCFFA30BFBFFFFBFE0FFFFF0FF9FFFFFFFFF9DFFFFFFFFF0F0FFFFD8FFFFFFFFFEC9EFDAFEFFEECF009E010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101FF00A157FFCFFFC8FF9B00007E2B",

        # "05AF46FCFFFFFFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF",
        # "05FF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13",
        # "05F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF139C3C",
        # "05F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7DFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7E7FF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7EFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7FFFF13F7E1FF13F7D5FF",
        # "05FF13F7FFFF13F7A5FF13F7FFFF13F7FFFF13F77BFF13F729FF13F7D7FF13F7FFFF13F7FFFF13F7A6FF13F7B8FF13F7E4FF13F79FFF13",
    ]
    
    for i, buffer in enumerate(test_buffers):
        data = bytearray.fromhex(buffer)
        if len(data) > 1:
            payload = data[1:]
            decoded_data = xor_decode(payload, key=255)
            decode_health_data(decoded_data)

def decode_health_data(decoded: bytes) -> DailyHealthData | None:

    # Example decoded: 000f0000001a010b153bacf50000000000001c050371
    # Offsets (Guessing based on typical Casio formats):
    # 0-4:  Header/Flags? (00 0f 00 00 00)
    # 5:    Year (1a -> 26 -> 2026)
        # 6:    Month (01)
        # 7:    Day (0b -> 11)
        # 8:    Hour (15 -> 21)
        # 9:    Minute (3b -> 59)
        # 10-11: Value A? (ac f5)
        # 12-17: Zeros?
        # 18-19: Value B? (1c 05 -> 1391? Steps?)
        # 20-21: Value C? (03 71 -> 881? Calories?)

        try:
            if len(decoded) < 20:
                logger.info(f"Decoded data too short to parse: {decoded.hex()}")
                return None
                
            year = decoded[5] + 2000
            month = decoded[6]
            day = decoded[7]
            hour = decoded[8]
            minute = decoded[9]
            
            # Assuming values from offsets:
            # Field 2 (Steps LE?) at 18:20
            # Field 3 (Cals?) at 20:22
            steps = int.from_bytes(decoded[18:20], 'little') 
            calories = int.from_bytes(decoded[20:22], 'little') if len(decoded) > 20 else 0
            
            from datetime import datetime
            dt = datetime(year, month, day, hour, minute)
            timestamp = int(dt.timestamp())
            
            snapshot = HealthData(
                timestamp=timestamp,
                steps=steps,
                calories=calories,
                distance=0, # Need to identify
                heart_rate_avg=0, # Need to identify
                heart_rate_max=0, # Need to identify
                heart_rate_min=0  # Need to identify
            )
            
            logger.info(f"Parsed Health Data: {snapshot}")
            
            # Return as a DailyHealthData object (containing this single snapshot for now)
            # In a real app, this would be aggregated.
            daily_data = DailyHealthData(
                date=dt.strftime("%Y-%m-%d"),
                snapshots=[snapshot]
            )
            
            # if HealthDataIO.on_data_update:
            #     HealthDataIO.on_data_update(daily_data)
                
            return daily_data

        except Exception as e:
            logger.error(f"Error parsing health data: {e}")
            return None

if __name__ == "__main__":
    run_hardcoded_test()
