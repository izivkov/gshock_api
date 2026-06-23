from collections.abc import Callable
from typing import Any, TypeVar

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.exc import BleakDBusError

from gshock_api import message_dispatcher
from gshock_api.casio_constants import CasioConstants
from gshock_api.exceptions import GShockConnectionError, GShockIgnorableException
from gshock_api.logger import logger
from gshock_api.scanner import scanner
from gshock_api.utils import to_casio_cmd

# Define a Type Variable T for generic request/message objects 
# as their specific class is not defined here.
T = TypeVar("T") 

# Define a type for the watch filter function. 
# It takes a BleakDevice object (the device found during scan) and returns a bool.
WatchFilter = Callable[[Any], bool] | None
# The scanner.scan returns a BleakDevice or None.
Device = Any | None


class Connection:
    """Manages the BLE connection to a G-Shock watch using Bleak."""
    
    # Class-level type alias for the handles map structure
    HandleMap = dict[int, str]

    def __init__(self, address: str | None = None) -> None:
        # Instance attributes with Type Hints
        self.handles_map: Connection.HandleMap = self.init_handles_map()
        self.address: str | None = address
        self.client: BleakClient | None = None
        self.characteristics_map: dict[str, str] = {} 

    def notification_handler(
        self, characteristic: BleakGATTCharacteristic, data: bytearray  # noqa: ARG002
    ) -> None:
        message_dispatcher.MessageDispatcher.on_received(data)

    async def init_characteristics_map(self) -> None:
        """
        Populates self.characteristics_map with UUIDs of all available characteristics.
        Manually injects specific characteristic UUIDs for testing purposes.
        """
        if self.client is None:
            return 
            
        services = self.client.services
        for service in services:
            for char in service.characteristics:
                # logger.info(f"Characteristics: {char.uuid}")
                self.characteristics_map[char.uuid] = char.uuid

        # --- Manual injection for GW-BX5600 testing ---
        # We manually ensure these UUIDs exist in the map so lookups don't fail
        
        # Configuration Notify (Handle 0x19 / 25)
        config_notify_uuid: str = CasioConstants.CASIO_GET_CONFIGURATION_CHARACTERISTIC_UUID
        self.characteristics_map[config_notify_uuid] = config_notify_uuid
        
        # Configuration Write (Handle 0x17 / 23)
        config_write_uuid: str = CasioConstants.CASIO_SET_CONFIGURATION_CHARACTERISTIC_UUID
        self.characteristics_map[config_write_uuid] = config_write_uuid
        
        # All Features Write (Handle 0x0E / 14)
        all_features_uuid: str = CasioConstants.CASIO_ALL_FEATURES_CHARACTERISTIC_UUID
        self.characteristics_map[all_features_uuid] = all_features_uuid

        logger.info("Manual characteristic injection complete for testing.")

    async def connect(self, watch_filter: WatchFilter = None) -> bool:
        """Connects to the G-Shock watch, optionally scanning if no address is provided."""
        try:
            if self.address is None:
                # scanner.scan is typed to return BleakDevice | None
                device: Device = await scanner.scan(
                    device_address=self.address,
                    watch_filter=watch_filter
                )
                if device is None:
                    logger.info("No G-Shock device found or name matches excluded watches.")
                    return False

                # BleakDevice has an address attribute
                self.address = device.address

            if self.address is None:
                return False 
            
            self.client = BleakClient(self.address)
            await self.client.connect()
            
            if not self.client.is_connected:
                logger.info(f"Failed to connect to {self.address}")
                return False

            await self.init_characteristics_map()

            await self.client.start_notify(
                CasioConstants.CASIO_ALL_FEATURES_CHARACTERISTIC_UUID,
                self.notification_handler,
            )

            return True

        except Exception as e:
            logger.info(f"[GShock Connect] Connection failed: {e}")
            return False
        
    async def disconnect(self) -> None:
        """Disconnects the BLE client if connected."""
        if self.client and self.client.is_connected:
            await self.client.disconnect()

    def is_service_supported(self, handle: int) -> bool:
        """Checks if a characteristic UUID mapped to a handle is present in the discovered characteristics."""
        uuid: str | None = self.handles_map.get(handle)
        return uuid is not None and uuid in self.characteristics_map

    async def write(self, handle: int, data: bytes) -> None:
        """Writes data to a characteristic identified by its handle."""
        try:
            uuid: str | None = self.handles_map.get(handle)

            if uuid is None or uuid not in self.characteristics_map:
                logger.info(
                    f"write failed: handle {handle} not in characteristics map"
                )
                if handle == 0x0D:
                    logger.info(
                        "Your watch does not support notifications..."
                    )
                return

            # 0x0E is CASIO_ALL_FEATURES_CHARACTERISTIC_UUID (requires response)
            response_type: bool = handle == 0x0E
            
            cmd_data: bytes = to_casio_cmd(data)

            if self.client:
                await self.client.write_gatt_char(
                    uuid, cmd_data, response=response_type
                )

        except Exception as e:
            e.args = (type(e).__name__,)
            if isinstance(e, (BleakDBusError, EOFError)):
                raise GShockIgnorableException(e) from e
            raise GShockConnectionError(f"Unable to send time to watch: {e}") from e

    # Replaced Any with TypeVar T
    async def request(self, request: T) -> None:
        """Sends a request using the read request characteristic handle (0x0C)."""
        await self.write(0x0C, request)

    def init_handles_map(self) -> dict[int, str]:
        """
        Initializes and returns the mapping of integer handles to characteristic UUIDs.
        Updated with handles 0x07, 0x17, and 0x19 from the CASIO GW-BX5600 logs.
        """
        handles_map: dict[int, str] = {}

        # Legacy and Core Handles
        handles_map[CasioConstants.HANDLE_DEVICE_NAME_LEGACY] = CasioConstants.CASIO_GET_DEVICE_NAME
        handles_map[CasioConstants.HANDLE_APPEARANCE] = CasioConstants.CASIO_APPEARANCE
        handles_map[CasioConstants.HANDLE_TX_POWER] = CasioConstants.TX_POWER_LEVEL_CHARACTERISTIC_UUID
        
        # Features and Time Sync Handles
        handles_map[CasioConstants.HANDLE_READ_ALL_FEATURES] = CasioConstants.CASIO_READ_REQUEST_FOR_ALL_FEATURES_CHARACTERISTIC_UUID
        handles_map[CasioConstants.HANDLE_ALL_FEATURES_NOTIFICATION] = CasioConstants.CASIO_NOTIFICATION_CHARACTERISTIC_UUID
        handles_map[CasioConstants.HANDLE_ALL_FEATURES_WRITE] = CasioConstants.CASIO_ALL_FEATURES_CHARACTERISTIC_UUID

        # New Handles identified from BT_HCI_2026_0108_170122_UTC+0800.log
        # Handle 7 (0x07)
        handles_map[CasioConstants.HANDLE_DEVICE_NAME_GW] = CasioConstants.CASIO_GET_DEVICE_NAME
        
        # Handle 14 (0x0E) - used for the final Time Command
        handles_map[CasioConstants.HANDLE_ALL_FEATURES_WRITE] = CasioConstants.CASIO_ALL_FEATURES_CHARACTERISTIC_UUID
        
        # Handle 23 (0x17)
        handles_map[CasioConstants.HANDLE_CONFIG_WRITE] = CasioConstants.CASIO_SET_CONFIGURATION_CHARACTERISTIC_UUID
        
        # Handle 25 (0x19) 
        handles_map[CasioConstants.HANDLE_CONFIG_NOTIFY] = CasioConstants.CASIO_GET_CONFIGURATION_CHARACTERISTIC_UUID

        # Add other legacy handles as needed...
        return handles_map

    # Replaced Any with TypeVar T
    async def send_message(self, message: T) -> None:
        """Sends a message to the watch using the message dispatcher."""
        await message_dispatcher.MessageDispatcher.send_to_watch(message)