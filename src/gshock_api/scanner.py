import sys

import time
from bleak import BleakScanner
from gshock_api.watch_info import watch_info
from gshock_api.logger import logger
from bleak.backends.device import BLEDevice

class Scanner:
    CASIO_SERVICE_UUID = "00001804-0000-1000-8000-00805f9b34fb"

    async def scan(self, device_address=None, excluded_watches: list[str] | None = None) -> BLEDevice | None:
        scanner = BleakScanner()

        if excluded_watches is None:
            excluded_watches = []

        if device_address is None:
            while True:
                device = await scanner.find_device_by_filter(
                    lambda d, ad: (
                        d.name
                        and (parts := d.name.split(" ", 1))
                        and parts[0].lower() == "casio"
                        and (len(parts) > 1 and parts[1] not in excluded_watches)
                    ),
                )

                # Trottle scan
                time.sleep(3)
                
                if device is None:
                    continue

                watch_info.set_name_and_model(device.name)
                break
        else:
            logger.info("Waiting for device by address...")
            device = await scanner.find_device_by_address(
                device_address, sys.float_info.max
            )
            if device is None:
                return None

            if any(device.name.lower().startswith(p.lower()) for p in excluded_watches):
                logger.info(f"Excluded device found: {device.name}")
                return None

            watch_info.set_name_and_model(device.name)

        return device

scanner = Scanner()
