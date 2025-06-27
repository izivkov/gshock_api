import sys

from bleak import BleakScanner
from gshock_api.configurator import conf
from gshock_api.watch_info import watch_info
from gshock_api.logger import logger
from gshock_api.device import Device 

class Scanner:
    CASIO_SERVICE_UUID = "00001804-0000-1000-8000-00805f9b34fb"

    async def scan(self, device_address=None) -> Device:
        scanner = BleakScanner()
        logger.info("Scanning for devices...")

        if device_address is None:
            while True:
                device = await scanner.find_device_by_filter(
                    lambda d, ad: d.name and d.name.lower().startswith("casio"),
                    timeout=5 * 60.0,
                )
                logger.info(f"device: {device}")
                if device is None:
                    continue
                
                # This is now set after connection in Connection class
                # watch_info.set_name_and_model(device.name)

                conf.put("device.address", device.address)
                conf.put("device.name", device.name)
                break
        else:
            logger.info("Waiting for device by address...")
            device = await scanner.find_device_by_address(
                device_address, sys.float_info.max
            )
            watch_info.set_name_and_model(device.name)

        return Device(device.name, device.address)

scanner = Scanner()
