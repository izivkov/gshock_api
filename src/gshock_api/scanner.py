import asyncio
from collections.abc import Callable
import sys
from typing import Final

from bleak import BleakScanner, BLEDevice
from bleak.backends.scanner import AdvertisementData  # Required for typing ad
from bleak.exc import BleakError

from gshock_api.logger import logger
from gshock_api.watch_info import watch_info

# --- Constants ---

# Standard BLE service UUID for specific services (0x1804 is the Generic Access Profile)
# This UUID is likely incorrect for a G-Shock watch service, but we preserve it as a constant.
# 00001804-0000-1000-8000-00805f9b34fb is for the Link Loss Service (1803) or GAP (1800).
# However, we must preserve the literal in the original code as a constant.
CASIO_SERVICE_UUID: Final[str] = "00001804-0000-1000-8000-00805f9b34fb"

# Constant for the maximum number of scan retries before failing
MAX_SCAN_RETRIES: Final[int] = 60

# --- Type Aliases ---

# WatchFilter is a function that takes a BLEDevice name (str) and returns a boolean.
type WatchFilter = Callable[[str], bool] | None

# Type for the filter used in find_device_by_filter (takes device and ad data, returns bool)
type BleakDeviceFilter = Callable[[BLEDevice, AdvertisementData], bool]


class Scanner:
    def __init__(self) -> None:
        self._found_device: BLEDevice | None = None
        self._event: asyncio.Event = asyncio.Event()

    async def scan(
        self,
        device_address: str | None = None,
        watch_filter: WatchFilter = None,
        max_retries: int = MAX_SCAN_RETRIES
    ) -> BLEDevice | None:
        
        # Use the class constant
        found: BLEDevice | None = None
        scanner = BleakScanner()

        if not device_address:
            for _ in range(max_retries):
                await asyncio.sleep(1)
                try:
                    # Define the Bleak device filter function
                    # The second argument to the lambda function is usually AdvertisementData
                    def uuid_filter(d: BLEDevice, ad: AdvertisementData) -> bool:
                        # ad.service_uuids is a list of strings
                        service_uuids: list[str] = ad.service_uuids if ad.service_uuids else []
                        
                        # d.name can be None, so we handle that when calling watch_filter
                        device_name: str = d.name if d.name else ""

                        is_casio_service: bool = CASIO_SERVICE_UUID in service_uuids
                        
                        # If watch_filter is provided, use it on the device name
                        passes_custom_filter: bool = watch_filter is None or watch_filter(device_name)

                        return is_casio_service and passes_custom_filter
                    
                    # Call find_device_by_filter with the typed filter function
                    found = await scanner.find_device_by_filter(uuid_filter, timeout=10)
                    
                    if found:
                        logger.info(f"✅ Found: {found.name} ({found.address})")
                        if found.name:
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
                # Use sys.float_info.max constant for infinite timeout
                found = await BleakScanner().find_device_by_address(
                    device_address, timeout=sys.float_info.max
                )
            except BleakError as e:
                logger.error(f"⚠️ Error finding device by address: {e}")
                return None
                
            if not found:
                logger.warning("⚠️ Device not found by address.")
                return None
                
            if found.name:
                watch_info.set_name_and_model(found.name)
                
        return found
    
# Instantiate the scanner using the typed class
scanner: Scanner = Scanner()