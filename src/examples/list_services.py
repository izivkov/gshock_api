import asyncio
from bleak import BleakScanner, BleakClient

async def list_services():
    device = await BleakScanner.find_device_by_name("CASIO DW-H5600")
    if not device:
        print("Device not found")
        return

    async with BleakClient(device) as client:
        print(f"Connected to {device.name}")
        for service in client.services:
            print(f"Service: {service.uuid} ({service.description})")
            for char in service.characteristics:
                print(f"  Characteristic: {char.uuid} ({char.description}) - {char.properties}")

if __name__ == "__main__":
    asyncio.run(list_services())
