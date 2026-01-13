import asyncio
from bleak import BleakScanner, BleakClient

# Casio-specific UUIDs
READ_REQ_UUID = "26eb002c-b012-49a8-b1f8-394fb2032b0f"
ALL_FEATURES_UUID = "26eb002d-b012-49a8-b1f8-394fb2032b0f"

async def main():
    print("Scanning for G-Shock DW-H5600...")
    
    device = await BleakScanner.find_device_by_filter(
        lambda d, ad: d.name and "CASIO DW-H5600" in d.name.upper()
    )

    if not device:
        print("Device not found.")
        return

    address = device.address
    print(f"Found {device.name} at {address}")

    client = BleakClient(address, timeout=20.0)
    
    try:
        # Connection with retries
        connected = False
        for attempt in range(3):
            try:
                print(f"\nConnection attempt {attempt + 1}...")
                await client.connect()
                
                print("Connected! Waiting 1s for stabilization...")
                await asyncio.sleep(1.0)
                
                print("Discovering services...")
                _ = client.services
                print("Services discovered.")
                connected = True
                break
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if client.is_connected:
                    await client.disconnect()
                
                if attempt < 2:
                    wait_time = 2 * (attempt + 1)
                    print(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)

        if not connected:
            print("\nFailed to establish stable connection.")
            return

        # Optional Pairing (can help on some systems)
        print("Attempting pairing (might be skipped if already bonded)...")
        try:
            await asyncio.wait_for(client.pair(), timeout=5.0)
            print("Pairing successful!")
        except Exception as e:
            print(f"Pairing info/skip: {e}")

        # Mandatory Casio Handshake
        print("Initializing watch (handshake write 0x10 to 26eb002c)...")
        # Handle 0x0C corresponds to CASIO_READ_REQUEST_FOR_ALL_FEATURES_CHARACTERISTIC_UUID
        await client.write_gatt_char(READ_REQ_UUID, b"\x10", response=False)
        
        await asyncio.sleep(1.0)
        print("Connection and initialization complete!")
        
        # Stay connected to verify
        print("Staying connected for 10 seconds. Watch should show 'Connected'.")
        for i in range(10):
            if not client.is_connected:
                print("\nWatch disconnected prematurely!")
                break
            await asyncio.sleep(1)
            print(f"{10-i}...", end=" ", flush=True)
        print("\nDone.")

    except Exception as e:
        print(f"\nError: {e}")
    finally:
        if client.is_connected:
            await client.disconnect()
            print("Disconnected.")

if __name__ == "__main__":
    asyncio.run(main())
