import sys

import asyncio
from bleak import BleakScanner
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
        excluded_watches: list[str] | None = None,
        max_retries: int = 60,  # Optional: to prevent infinite loops
    ) -> BLEDevice | None:
        scanner = BleakScanner()
        excluded_watches = excluded_watches or []

        retries = 0
        device = None

        if device_address is None:
            while retries < max_retries:
                await asyncio.sleep(1)
                try:                
                    def casio_filter(device: BLEDevice, advertisement_data) -> bool:
                        if not device.name:
                            return False

                        parts = device.name.split(" ", 1)
                        if not parts:
                            return False

                        is_casio = parts[0].lower() == "casio"
                        is_excluded = len(parts) > 1 and parts[1] in excluded_watches

                        return is_casio and not is_excluded
                    
                    device = await scanner.find_device_by_filter(
                        casio_filter,
                        timeout=10,
                    )

                    if device:
                        logger.info(f"✅ Found: {device.name} ({device.address})")
                        watch_info.set_name_and_model(device.name)
                        return device
                    else:
                        retries += 1
                        logger.debug(f"⚠️ No matching device found, retry {retries}...")

                except BleakError as e:
                    logger.warning(f"⚠️ BLE scan error: {e}")
                    retries += 1

            logger.error("⚠️ Max retries reached. No device found.")
            return None

        else:
            logger.info(f"⚠️ Waiting for specific device by address: {device_address}...")
            try:
                device = await scanner.find_device_by_address(
                    device_address, timeout=sys.float_info.max
                )
            except BleakError as e:
                logger.error(f"⚠️ Error finding device by address: {e}")
                return None

            if device is None:
                logger.warning("⚠️ Device not found by address.")
                return None

            if any(device.name.lower().startswith(p.lower()) for p in excluded_watches):
                logger.info(f"Excluded device found: {device.name}")
                return None

            watch_info.set_name_and_model(device.name)
            return device

    async def scan_with_discover(self, device_address: Optional[str] = None, excluded_watches: Optional[list[str]] = None) -> Optional[BLEDevice]:
        if excluded_watches is None:
            excluded_watches = []

        logger.info("🔍 Scanning for CASIO device...")

        try:
            while True:
                try:
                    devices = await BleakScanner.discover(timeout=5.0)
                except Exception as e:
                    logger.warning(f"⚠️ Scan error: {e}")
                    await asyncio.sleep(1)
                    continue

                if not devices:
                    logger.debug("No BLE devices found.")
                    await asyncio.sleep(1)
                    continue

                for device in devices:
                    name = device.name or ""
                    parts = name.split(" ", 1)
                    is_casio = parts[0].lower() == "casio"
                    is_excluded = len(parts) > 1 and parts[1] in excluded_watches
                    if is_excluded:
                        logger.info(f"{name} excluded!")

                    if is_casio and not is_excluded:
                        logger.info(f"✅ Found: {name} ({device.address})")
                        watch_info.set_name_and_model(device.name)
                        return device

                await asyncio.sleep(1)  # ✅ Wait before next loop

        except asyncio.CancelledError:
            logger.info("🔁 Scan loop cancelled.")
            raise

        except Exception as e:
            logger.exception(f"❌ Unexpected scan error: {e}")
            return None
    
scanner = Scanner()
