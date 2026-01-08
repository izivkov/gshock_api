from dataclasses import dataclass
from typing import Optional
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.logger import logger

@dataclass
class HealthData:
    steps: int = 0
    calories: int = 0
    timestamp: int = 0

class HealthDataIO:
    @staticmethod
    async def request(connection: ConnectionProtocol, cmd_hex: str = "002E51B9030000") -> None:
        """
        Request health data from the watch.
        """
        logger.info(f"Sending health data request: {cmd_hex}")
        cmd = bytes.fromhex(cmd_hex)
        
        # Use 0x10 handle (CASIO_DATA_REQUEST_SP_CHARACTERISTIC_UUID)
        await connection.write(0x10, cmd)

    @staticmethod
    def xor_decode(data: bytes, key: int = 255) -> bytes:
        return bytes([b ^ key for b in data])

    @staticmethod
    def on_received(data: bytes) -> None:
        """
        Handles incoming health data notifications.
        Data format is expected to be XOR encoded with key 255.
        """
        logger.info(f"HealthDataIO received: {data.hex()}")
        
        # The first byte is the header (0x05), the rest is the payload
        payload = data[1:]
        decoded = HealthDataIO.xor_decode(payload, key=255)
        logger.info(f"Decoded Health Data: {decoded.hex()}")
        
        # Example parsing based on fa 56 14 00 ... 
        # fa 56 14 00 (0x001456FA = 1,333,498? No, likely little endian)
        # 0x001456FA is 1,333,242. 
        # fa 56 is 22170. 
        # We need more samples to be sure about the parsing.
        # But for now, we just log the decoded hex.
