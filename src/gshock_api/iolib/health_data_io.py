import json
from typing import Optional
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.logger import logger
from gshock_api.cancelable_result import CancelableResult
from gshock_api.health_data import HealthData, DailyHealthData

from collections.abc import Callable

class HealthDataIO:
    result: CancelableResult = None
    connection: ConnectionProtocol = None

    on_data_update: Optional[Callable[[DailyHealthData], None]] = None

    @staticmethod
    async def request(connection: ConnectionProtocol) -> CancelableResult[str]:
        HealthDataIO.connection = connection
        await connection.request("002EFFFFFFFFFF")
        HealthDataIO.result = CancelableResult()
        return await HealthDataIO.result.get_result()

    @staticmethod
    async def send_to_watch(message: str) -> None:
        """Wrapper to conform to MessageDispatcher's send_to_watch pattern.
        Delegates to :meth:`request` which performs the health‑data request.
        """
        import asyncio

        # Default command to request health data
        cmd_hex = "002E51B9030000"
        
        # Try to parse custom command from message if provided
        try:
            parsed = json.loads(message)
            if "value" in parsed:
                cmd_hex = parsed["value"]
        except Exception:
            pass

        logger.info(f"HealthDataIO: Starting data request sequence for {cmd_hex}")
        
        # 1. Send Request on 0x11
        # 0x11 -> CASIO_DATA_REQUEST_SP_CHARACTERISTIC_UUID
        await HealthDataIO.connection.write(0x11, cmd_hex)
        
        # 2. Handshake on Convoy (0x14)
        # 0x14 -> CASIO_CONVOY_CHARACTERISTIC_UUID
        convoy_steps = [
            ("000000", 1.0),
            ("000000", 1.0),
            ("04000000000000000000", 0.5),
            ("0401180018000000DC05", 0.5),
            ("0600000000000000000000000000", 1.0),
            ("06FA00001000000002", 1.0),
        ]
        
        for data, delay in convoy_steps:
            await HealthDataIO.connection.write(0x14, data)
            await asyncio.sleep(delay)

        # 3. Ack the request/Response on 0x11
        # Note: Ideally we wait for the 002E... response notification and mirror it.
        # For now, using the value seen in logs which corresponds to an ACK.
        # This seems to verify we are ready to receive.
        ack_payload = "002E0014000000" 
        await HealthDataIO.connection.write(0x11, ack_payload)
        await asyncio.sleep(0.5)

        # 4. Final Convoy Handshake to trigger stream
        await HealthDataIO.connection.write(0x14, "070000000000000000000000000000")
        logger.info("HealthDataIO: Sent final handshake, expecting data stream...")

    @staticmethod
    def xor_decode(data: bytes, key: int = 255) -> bytes:
        return bytes([b ^ key for b in data])

    @staticmethod
    def on_received(data: bytes) -> None:
        """
        Handles incoming health data notifications.
        Data format is expected to be XOR encoded with key 255.
        """
        logger.info(f"HealthDataIO received hex: {data.hex()}")
        
        decoded_data = None
        if len(data) > 1:
            payload = data[1:]
            decoded = HealthDataIO.xor_decode(payload, key=255)
            logger.info(f"HealthDataIO decoded: {decoded.hex()}")
            decoded_data = HealthDataIO.decode_health_data(decoded)

        HealthDataIO.result.set_result(decoded_data)

    @staticmethod
    def on_received_response(data: bytes) -> None:
        """
        Handles incoming command responses (0x00... or 0x07... or 0x11...).
        Routes logic for Heart Rate parsing and packet echoing.
        """
        hex_data = data.hex()
        logger.info(f"HealthDataIO received response: {hex_data}")

        # 2. Check for the pattern 00 2E ... or 07 2E ... (Handshake Echo)
        if hex_data.startswith("002e") or hex_data.startswith("072e"):
            # Echo logic
            if HealthDataIO.connection:
                logger.info(f"HealthDataIO: Echoing request packet {hex_data} to continue stream...")
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(HealthDataIO.connection.write(0x11, hex_data))
                except RuntimeError:
                    logger.error("HealthDataIO: No event loop to schedule echo write")

    @staticmethod
    def on_received_request_notification(data: bytes) -> None:
        # Forward to main response handler as they share logic
        HealthDataIO.on_received_response(data)

    @staticmethod
    def decode_health_data(decoded: bytes) -> DailyHealthData | None:
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
            
            if HealthDataIO.on_data_update:
                HealthDataIO.on_data_update(daily_data)
                
            return daily_data

        except Exception as e:
            logger.error(f"Error parsing health data: {e}")
            return None
