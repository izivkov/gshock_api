import logging
import os
import sys

# Add src to path so we can import gshock_api
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gshock_api.iolib.health_data_io import HealthDataIO
from gshock_api.logger import logger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

def run_hardcoded_test():
    logger.info("Starting Hardcoded Health Parser Test (FINAL)...")
    
    test_buffers = [
        # 1. Jan 7 Live Update (Steps 0, Calories 702) - RAW
        "05FFF0FFFFFFE5FEF8F1DFC9BAFFFFFFFFFFFF41FDEF7B", 
        
        # 2. Jan 6 History Record (Steps 1268, Calories 1780) - RAW
        # This is a segment from a long buffer that contains: 26 01 07 ec ...
        "059C8DFFFFFFD9FEF813A2D185FCFFA30BFBFFFFBFE0FFFFF0FF9FFFFFFFFF9DFFFFFFFFF0F0FFFFD8FFFFFFFFFEC9EFDAFEFFEECF009E010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101FF00A157FFCFFFC8FF9B00007E2B",
        
        # 3. Real-time HR: 86 BPM - RAW
        # Original decoded: 07 d1 56 d3 0d 00 00
        "072EA92CF2FFFF",

        # 4. Real-time HR: 81 BPM - RAW
        # Original decoded: 07 d1 51 b9 03 00 00
        "072EAE46FCFFFF",
    ]
    
    for i, buf_hex in enumerate(test_buffers):
        print(f"\n--- Testing Buffer {i} ---")
        HealthDataIO.on_received(bytes.fromhex(buf_hex))

if __name__ == "__main__":
    run_hardcoded_test()
