import asyncio
from collections.abc import Callable
from typing import Any, TypeVar

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.exc import BleakDBusError

# New imports for Linux Pairing Agent
from bluez_peripheral.util import get_message_bus
from bluez_peripheral.agent import NoIoAgent

from gshock_api import message_dispatcher
from gshock_api.casio_constants import CasioConstants
from gshock_api.exceptions import GShockConnectionError, GShockIgnorableException
from gshock_api.logger import logger
from gshock_api.scanner import scanner
from gshock_api.utils import to_casio_cmd

T = TypeVar("T") 
WatchFilter = Callable[[Any], bool] | None
Device = Any | None

class Connection:
    """Manages the BLE connection and pairing agent for G-Shock watches on Linux."""
    
    HandleMap = dict[int, str]

    def __init__(self, address: str | None = None) -> None:
        self.handles_map: Connection.HandleMap = self.init_handles_map()
        self.address: str | None = address
        self.client: BleakClient | None = None
        self.characteristics_map: dict[str, str] = {} 
        
        # Internals for BlueZ Agent
        self._bus = None
        self._agent = None

    async def _setup_agent(self):
        """Registers a NoIoAgent to handle pairing prompts programmatically."""
        try:
            if self._bus is None:
                self._bus = await get_message_bus()
            
            if self._agent is None:
                self._agent = NoIoAgent()
                # 'default=True' lets this script catch pairing requests from the OS.
                # This call requires the script to be run with sudo.
                await self._agent.register(self._bus, default=True)
                logger.info("Linux Bluetooth Pairing Agent registered.")
        except Exception as e:
            logger.error(f"Failed to register Pairing Agent: {e}. Check sudo permissions.")

    def disconnected_callback(self, client: BleakClient) -> None:
        """Invoked when the watch disconnects."""
        logger.info(f"Disconnected from watch at {client.address}")

    def notification_handler(
        self, characteristic: BleakGATTCharacteristic, data: bytearray
    ) -> None:
        logger.info(f"Notification received on {characteristic.uuid}: {data.hex()}")
        message_dispatcher.MessageDispatcher.on_received(data)

    async def init_characteristics_map(self) -> None:
        """Populates self.characteristics_map with UUIDs of all available characteristics."""
        if self.client is None:
            return 
            
        services = self.client.services
        logger.info("Starting service discovery...")
        for service in services:
            for char in service.characteristics:
                self.characteristics_map[char.uuid] = char.uuid
                logger.debug(f"Discovered characteristic: {char.uuid} (Handle: {char.handle})")

    async def connect(self, watch_filter: WatchFilter = None) -> bool:
        """Connects and pairs with the G-Shock watch."""
        try:
            # Setup the background pairing agent
            await self._setup_agent()

            if self.address is None:
                device: Device = await scanner.scan(
                    device_address=self.address,
                    watch_filter=watch_filter
                )
                if device is None:
                    logger.info("No G-Shock device found or name matches excluded watches.")
                    return False
                self.address = device.address

            if self.address is None:
                return False 
            
            self.client = BleakClient(
                self.address, 
                timeout=20.0,
                disconnected_callback=self.disconnected_callback
            )

            logger.info(f"Connecting and pairing with {self.address}...")
            
            for attempt in range(3):
                try:
                    await asyncio.sleep(0.5)
                    await self.client.connect()
                    
                    # On Linux, explicitly triggering .pair() ensures the Agent 
                    # handshakes with the watch and stores the bond in BlueZ.
                    logger.info("Initiating bonding...")
                    await self.client.pair()
                    
                    logger.info(f"Connection attempt {attempt + 1} successful.")
                    break
                except Exception as e:
                    if attempt == 2:
                        raise e
                    logger.warning(f"Connection attempt {attempt + 1} failed: {e}. Retrying...")
                    await asyncio.sleep(2)
            
            if not self.client.is_connected:
                return False

            logger.info("Connection established. Waiting 1.0s to stabilize...")
            await asyncio.sleep(1.0)

            discovery_success = False
            for discovery_attempt in range(3):
                try:
                    await self.init_characteristics_map()
                    discovery_success = True
                    break
                except Exception as e:
                    logger.warning(f"Discovery attempt {discovery_attempt + 1} failed. Retrying...")
                    await asyncio.sleep(1.0)

            if not discovery_success:
                logger.error("Service discovery failed. Device likely disconnected.")
                await self.disconnect()
                return False

            # Characteristics to notify
            uuids_to_notify = [
                CasioConstants.CASIO_ALL_FEATURES_CHARACTERISTIC_UUID,
                CasioConstants.CASIO_CONVOY_CHARACTERISTIC_UUID,
                CasioConstants.CASIO_DATA_REQUEST_SP_CHARACTERISTIC_UUID
            ]

            for uuid in uuids_to_notify:
                if uuid in self.characteristics_map:
                    await self.client.start_notify(uuid, self.notification_handler)

            return True

        except Exception as e:
            logger.info(f"[GShock Connect] Connection failed: {e}")
            return False
        
    async def disconnect(self) -> None:
        """Disconnects the BLE client."""
        if self.client and self.client.is_connected:
            await self.client.disconnect()

    def is_service_supported(self, handle: int) -> bool:
        uuid: str | None = self.handles_map.get(handle)
        return uuid is not None and uuid in self.characteristics_map

    async def write(self, handle: int, data: bytes | str) -> None:
        """Writes data to a characteristic identified by its handle."""
        try:
            uuid: str | None = self.handles_map.get(handle)

            if uuid is None or uuid not in self.characteristics_map:
                logger.info(f"write failed: handle {handle} not in map")
                return

            response_type: bool = handle in [0x0E, 0x11]
            cmd_data = to_casio_cmd(data) if isinstance(data, str) else bytes(data)

            if self.client:
                logger.info(f"Writing to {uuid} (handle {handle:02X}): {cmd_data.hex()}")
                await self.client.write_gatt_char(uuid, cmd_data, response=response_type)

        except Exception as e:
            if isinstance(e, (BleakDBusError, EOFError)):
                raise GShockIgnorableException(e) from e
            raise GShockConnectionError(f"Unable to send data: {e}") from e

    async def request(self, request: T) -> None:
        """Sends a request using handle 0x0C."""
        await self.write(0x0C, request)

    def init_handles_map(self) -> HandleMap:
        """Initializes and returns the mapping of integer handles to characteristic UUIDs."""
        handles_map: Connection.HandleMap = {}

        handles_map[0x04] = CasioConstants.CASIO_GET_DEVICE_NAME
        handles_map[0x06] = CasioConstants.CASIO_APPEARANCE
        handles_map[0x09] = CasioConstants.TX_POWER_LEVEL_CHARACTERISTIC_UUID
        handles_map[0x0C] = CasioConstants.CASIO_READ_REQUEST_FOR_ALL_FEATURES_CHARACTERISTIC_UUID
        handles_map[0x0E] = CasioConstants.CASIO_ALL_FEATURES_CHARACTERISTIC_UUID
        handles_map[0x0D] = CasioConstants.CASIO_NOTIFICATION_CHARACTERISTIC_UUID
        handles_map[0x11] = CasioConstants.CASIO_DATA_REQUEST_SP_CHARACTERISTIC_UUID
        handles_map[0x14] = CasioConstants.CASIO_CONVOY_CHARACTERISTIC_UUID
        handles_map[0xFF] = CasioConstants.SERIAL_NUMBER_STRING

        return handles_map

    # Replaced Any with TypeVar T
    async def send_message(self, message: T) -> None:
        """Sends a message to the watch using the message dispatcher."""
        await message_dispatcher.MessageDispatcher.send_to_watch(message)
