import sys

import asyncio
from gshock_api.watch_info import watch_info
from gshock_api.logger import logger
from bleak.backends.device import BLEDevice
from bleak import BleakScanner, BLEDevice
from bleak.exc import BleakError
from typing import Optional

class Scanner:
    def __init__(self):
        self._found_device: Optional[BLEDevice] = None
        self._event = asyncio.Event()

    async def scan(
        self,
        device_address: str | None = None,
        watch_filter=None,
        max_retries: int = 60
    ) -> BLEDevice | None:
        
        CASIO_SERVICE_UUID = "00001804-0000-1000-8000-00805f9b34fb"
        found = None

        if not device_address:
            for _ in range(max_retries):
                await asyncio.sleep(1)
                try:
                    def uuid_filter(d: BLEDevice, ad):
                        su = ad.service_uuids or []
                        return CASIO_SERVICE_UUID in su and (watch_filter is None or watch_filter(d.name))
                    found = await BleakScanner().find_device_by_filter(uuid_filter, timeout=10)
                    if found:
                        logger.info(f"✅ Found: {found.name} ({found.address})")
                        watch_info.set_name_and_model(found.name)
                        return found
                    logger.debug("⚠️ No matching device found, retrying...")
                except BleakError as e:
                    logger.warning(f"⚠️ BleakError: BLE scan error: {e}")
                except Exception as e:
                    logger.warning(f"⚠️ BLE scan error: {e}")

            logger.error("⚠️ Max retries reached. No device found.")
        else:
            logger.info(f"⚠️ Waiting for specific device by address: {device_address}...")
            try:
                found = await BleakScanner().find_device_by_address(
                    device_address, timeout=sys.float_info.max
                )
            except BleakError as e:
                logger.error(f"⚠️ Error finding device by address: {e}")
                return None
            if not found:
                logger.warning("⚠️ Device not found by address.")
                return None
            watch_info.set_name_and_model(found.name)
        return found
    
scanner = Scanner()
