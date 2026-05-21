import json
from datetime import datetime, timedelta
from typing import Optional
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.logger import logger
from gshock_api.cancelable_result import CancelableResult
from gshock_api.health_data import HealthData, DailyHealthData

from collections.abc import Callable

class HealthDataIO:
    indices: list[str] = ["64", "63", "62", "61", "60"]
    result: CancelableResult = None
    connection: ConnectionProtocol = None

    on_data_update: Optional[Callable[[DailyHealthData], None]] = None

    @staticmethod
    async def request(connection: ConnectionProtocol) -> CancelableResult[str]:
        HealthDataIO.connection = connection
        HealthDataIO.result = CancelableResult()
        await HealthDataIO.get_data()
        return await HealthDataIO.result.get_result()

    @staticmethod
    async def get_data() -> None:
        """Wrapper to perform the health‑data request."""
        import asyncio

        # 0. Initial reset/request info
        logger.info("HealthDataIO: Initializing health data request...")
        await HealthDataIO.connection.write(0x11, "002EFFFFFFFFFF")
        await asyncio.sleep(0.5)
        await HealthDataIO.connection.write(0x11, "002E0014000000")
        await asyncio.sleep(1.0)
        
        # 4. Request summaries slowly to avoid EOF
        for idx in HealthDataIO.indices:
            cmd_hex = f"002E{idx}72000000"
            logger.info(f"HealthDataIO: Requesting index {idx}: {cmd_hex}")
            await HealthDataIO.connection.write(0x11, cmd_hex)
            await HealthDataIO.connection.write(0x14, "070000000000000000000000000000")
            await asyncio.sleep(5.0)
        
        logger.info("HealthDataIO: History request sequence complete.")

    @staticmethod
    def xor_decode(data: bytes, key: int = 255) -> bytes:
        return bytes([b ^ key for b in data])

    @staticmethod
    def decode_health_data(decoded: bytes) -> list[DailyHealthData]:
        """
        Decodes G-Shock health data buffers.

        Two known formats (after XOR decode with key=0xFF):

        Live Update (signature 0x00 0x0F):
            [5]     Year (hex, e.g. 0x1a = 26 -> 2026)
            [6]     Month (1-12)
            [7]     Day (1-31)
            [8]     Hour (0-23)
            [9]     Minute (0-59)
            [15:17] Steps (16-bit LE)
            [18:20] Calories (16-bit LE, direct kcal)

        Historical Day Summary (signature byte[0]=index, byte[1]=0x72):
            [5]     Year (0x26 = 2026)
            [6]     Month (1-12)
            [7]     Day (NOTE: actual data is for day-1)
            [11:13] Calories/2 (16-bit LE, multiply by 2 for kcal)
            [15:17] Steps (16-bit LE)
            [19:21] Distance in decimeters (16-bit LE, divide by 10 for meters)
        """
        results = []
        if len(decoded) < 16:
            return results

        # Buffer Identification
        # decoded[0] = index or type prefix, decoded[1] = sub-type
        msg_type = decoded[1]

        try:
            # --- Type 1: Live Update / Current Day Snapshot (Signature XX 0F) ---
            if msg_type == 0x0F:
                dt = HealthDataIO._parse_live_date(decoded)
                if not dt:
                    return results
                
                steps = int.from_bytes(decoded[15:17], 'little')
                calories = int.from_bytes(decoded[18:20], 'little')
                
                date_str = dt.strftime("%Y-%m-%d")
                results.append(DailyHealthData(
                    date=date_str,
                    snapshots=[HealthData(int(dt.timestamp()), steps, calories)]
                ))
                return results

            # --- Type 2: Historical Day Summary (Signature XX 72) ---
            if msg_type == 0x72:
                dt_header = HealthDataIO._parse_history_date(decoded)
                if not dt_header:
                    return results
                
                # The header date is one day AFTER the actual activity date
                dt_local = dt_header - timedelta(days=1)
                date_str = dt_local.strftime("%Y-%m-%d")
                
                # Calories stored at half value at offset 11-12
                calories = int.from_bytes(decoded[11:13], 'little') * 2
                # Steps at offset 15-16
                steps = int.from_bytes(decoded[15:17], 'little')
                # Distance in decimeters at offset 19-20
                distance = int.from_bytes(decoded[19:21], 'little') // 10 if len(decoded) >= 21 else 0
                
                results.append(DailyHealthData(
                    date=date_str,
                    snapshots=[HealthData(int(dt_local.timestamp()), steps, calories, distance)]
                ))
                return results

        except Exception as e:
            logger.error(f"Error parsing health data: {e}")
            
        return results

    @staticmethod
    def _parse_live_date(decoded: bytes) -> Optional[datetime]:
        """Parse date/time from a live update buffer (000f format).
        
        Year is stored as hex value at offset 5 (e.g. 0x1a = 26 -> 2026).
        Month, day, hour, minute are straight hex values.
        """
        if len(decoded) < 10:
            return None
        try:
            year = 2000 + decoded[5]
            month = decoded[6]
            day = decoded[7]
            hour = decoded[8]
            minute = decoded[9]
            
            if not (1 <= month <= 12 and 1 <= day <= 31):
                return None
            if hour >= 24:
                hour = 0
            if minute >= 60:
                minute = 0
                
            return datetime(year, month, day, hour, minute)
        except (ValueError, OverflowError):
            return None

    @staticmethod
    def _parse_history_date(decoded: bytes) -> Optional[datetime]:
        """Parse date from a historical summary buffer (XX72 format).
        
        Year at offset 5: 0x26 means 2026 (hex year code).
        Month/day are hex values at offsets 6 and 7.
        """
        if len(decoded) < 8:
            return None
        try:
            y_raw = decoded[5]
            month = decoded[6]
            day = decoded[7]
            
            # Year encoding: 0x26 = 38 decimal, but represents 2026
            # The pattern is: year is stored as hex where 0x26 = 2026
            # (i.e. the hex digits form the last two digits of the year)
            if y_raw == 0x26:
                year = 2026
            elif y_raw == 0x25:
                year = 2025
            elif y_raw == 0x27:
                year = 2027
            elif y_raw < 100:
                year = 2000 + y_raw
            else:
                year = 2000 + (y_raw & 0x3F)
            
            if not (1 <= month <= 12 and 1 <= day <= 31):
                return None
                
            return datetime(year, month, day)
        except (ValueError, OverflowError):
            return None

    @staticmethod
    def on_received(data: bytes) -> None:
        """Called when characteristic 0x05 (health data) is received."""
        if not data: return
        payload = data[1:]
        decoded = HealthDataIO.xor_decode(payload, key=255)
        logger.info(f"HealthDataIO decoded (raw): {decoded.hex()}")
        
        found_records = HealthDataIO.decode_health_data(decoded)
        for record in found_records:
            logger.info(f"HealthDataIO: Successfully extracted record for {record.date}")
            logger.info(f"  Steps: {record.total_steps}, Calories: {record.total_calories} kcal, Distance: {record.total_distance} m")
            if HealthDataIO.on_data_update:
                HealthDataIO.on_data_update(record)
            
        if HealthDataIO.result and not HealthDataIO.result.done():
            if found_records:
                HealthDataIO.result.set_result(found_records[0])

    @staticmethod
    def on_received_response(data: bytes) -> None:
        """Handles incoming command responses (0x11)."""
        hex_data = data.hex()
        logger.info(f"HealthDataIO received response: {hex_data}")

        if hex_data.startswith("002e") or hex_data.startswith("072e"):
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
        HealthDataIO.on_received_response(data)
