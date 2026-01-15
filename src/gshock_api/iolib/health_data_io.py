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
    def bcd_to_int(bcd: int) -> int:
        return ((bcd >> 4) * 10) + (bcd & 0x0F)

    @staticmethod
    def decode_health_data(decoded: bytes) -> list[DailyHealthData]:
        """
        Decodes G-Shock health data buffers based on signatures found in health_hardcoded_test.py.
        """
        results = []
        if len(decoded) < 16:
            return results

        # Buffer Identification
        # decoded[0] index, decoded[1] type
        msg_type = decoded[1]

        try:
            # --- Type 1: Live Update / Current Day Snapshot (Signature XX 0F) ---
            if msg_type == 0x0f:
                dt = HealthDataIO.try_parse_date_internal(
                    decoded[5], decoded[6], decoded[7], decoded[8], decoded[9]
                )
                if not dt:
                    return results
                
                # Offsets: 15-16 Steps, 18-19 Calories, 20-21 Distance
                steps = int.from_bytes(decoded[15:17], 'little')
                calories = int.from_bytes(decoded[18:20], 'little')
                distance = int.from_bytes(decoded[20:22], 'little') // 10 if len(decoded) >= 22 else 0
                
                date_str = dt.strftime("%Y-%m-%d")
                results.append(DailyHealthData(
                    date=date_str,
                    snapshots=[HealthData(int(dt.timestamp()), steps, calories, distance)]
                ))
                return results

            # --- Type 2: Historical Day Summary (Signature XX 72) ---
            if msg_type == 0x72:
                dt_watch = HealthDataIO.try_parse_date_internal(
                    decoded[5], decoded[6], decoded[7]
                )
                if not dt_watch:
                    return results
                
                # Adjust for activity date (-1 day)
                dt_local = dt_watch - timedelta(days=1)
                date_str = dt_local.strftime("%Y-%m-%d")
                
                # Offsets: 11-12 Calories (* 2), 15-16 Steps, 19-20 Distance
                calories = int.from_bytes(decoded[11:13], 'little') * 2
                steps = int.from_bytes(decoded[15:17], 'little')
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
    def try_parse_date_internal(y_raw, m_raw, d_raw, h_raw=0, min_raw=0) -> Optional[datetime]:
        """Tries to parse date/time parts as either BCD or Hex."""
        # Try BCD first
        try:
            y, m, d = 2000+HealthDataIO.bcd_to_int(y_raw), HealthDataIO.bcd_to_int(m_raw), HealthDataIO.bcd_to_int(d_raw)
            h, mn = HealthDataIO.bcd_to_int(h_raw), HealthDataIO.bcd_to_int(min_raw)
            if 1 <= m <= 12 and 1 <= d <= 31:
                return datetime(y, m, d, h if h < 24 else 0, mn if mn < 60 else 0)
        except: pass
        # Try Hex fallback
        try:
            if 1 <= m_raw <= 12 and 1 <= d_raw <= 31:
                return datetime(2000+y_raw, m_raw, d_raw, h_raw if h_raw < 24 else 0, min_raw if min_raw < 60 else 0)
        except: pass
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
