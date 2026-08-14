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

T = TypeVar("T")

WatchFilter = Callable[[Any], bool] | None
Device = Any | None


class Connection:
    """Manages the BLE connection to a G-Shock watch using Bleak."""

    HandleMap = dict[int, str]

    def __init__(self, address: str | None = None) -> None:
        self.handles_map: Connection.HandleMap = self.init_handles_map()
        self.address: str | None = address
        self.client: BleakClient | None = None
        self.characteristics_map: dict[str, str] = {}

    def notification_handler(
        self, characteristic: BleakGATTCharacteristic, data: bytearray  # noqa: ARG002
    ) -> None:
        message_dispatcher.MessageDispatcher.on_received(data)

    async def init_characteristics_map(self) -> None:
        """Populates self.characteristics_map with UUIDs of all available characteristics."""
        if self.client is None:
            return

        services = self.client.services
        for service in services:
            for char in service.characteristics:
                self.characteristics_map[char.uuid] = char.uuid

    async def connect(self, watch_filter: WatchFilter = None) -> bool:
        """Connects to the G-Shock watch, optionally scanning if no address is provided."""
        try:
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

            self.client = BleakClient(self.address)
            await self.client.connect()

            if not self.client.is_connected:
                logger.info(f"Failed to connect to {self.address}")
                return False

            await self.init_characteristics_map()

            # Subscribe to notifications on every characteristic that supports
            # them. This makes the connection self-adapting across all watch
            # models without needing per-model whitelists or hardcoded UUIDs.
            for service in self.client.services:
                for char in service.characteristics:
                    if "notify" in char.properties or "indicate" in char.properties:
                        try:
                            await self.client.start_notify(
                                char.uuid, self.notification_handler
                            )
                            logger.info(f"Subscribed to notifications: {char.uuid}")
                        except Exception as e:
                            logger.debug(f"start_notify failed for {char.uuid}: {e}")

            return True

        except Exception as e:
            logger.info(f"[GShock Connect] Connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnects the BLE client if connected."""
        if self.client and self.client.is_connected:
            await self.client.disconnect()

    # Handles that require write-without-response
    NO_RESPONSE_HANDLES: frozenset[int] = frozenset({
        0x0C,  # READ_ALL_FEATURES    — WRITE_NO_RESP
        0x0D,  # ALL_FEATURES_NOTIFY  — WRITE_NO_RESP  
        0x11,  # DATA_REQUEST_SP      — actually WRITE (has response) but used as GET
        0x14,  # CONVOY               — WRITE_NO_RESP
        0x17,  # SP_REQUEST           — WRITE_NO_RESP confirmed from log
    })

    async def write(self, handle: int, data: bytes | str) -> None:
        try:
            uuid: str | None = self.handles_map.get(handle)

            if uuid is None or uuid not in self.characteristics_map:
                logger.info(f"write failed: handle {handle} not in characteristics map")
                if handle == 0x0D:
                    logger.info("Your watch does not support notifications...")
                return

            response_type: bool = handle not in self.NO_RESPONSE_HANDLES
            cmd_data: bytes = to_casio_cmd(data) if isinstance(data, str) else bytes(data)

            if self.client:
                await self.client.write_gatt_char(uuid, cmd_data, response=response_type)

        except Exception as e:
            e.args = (type(e).__name__,)
            if isinstance(e, (BleakDBusError, EOFError)):
                raise GShockIgnorableException(e) from e
            raise GShockConnectionError(f"Unable to send time to watch: {e}") from e

    async def request(self, request: T) -> None:
        """Sends a request using the read request characteristic handle (0x0C)."""
        await self.write(0x0C, request)

    def init_handles_map(self) -> HandleMap:
        """Initializes and returns the mapping of integer handles to characteristic UUIDs."""
        handles_map: Connection.HandleMap = {}

        handles_map[0x04] = CasioConstants.CASIO_GET_DEVICE_NAME
        handles_map[0x06] = CasioConstants.CASIO_APPEARANCE
        handles_map[0x09] = CasioConstants.TX_POWER_LEVEL_CHARACTERISTIC_UUID
        handles_map[0x0C] = CasioConstants.CASIO_READ_REQUEST_FOR_ALL_FEATURES_CHARACTERISTIC_UUID
        handles_map[0x0D] = CasioConstants.CASIO_NOTIFICATION_CHARACTERISTIC_UUID
        handles_map[0x0E] = CasioConstants.CASIO_ALL_FEATURES_CHARACTERISTIC_UUID
        handles_map[0x11] = CasioConstants.CASIO_DATA_REQUEST_SP_CHARACTERISTIC_UUID
        handles_map[0x14] = CasioConstants.CASIO_CONVOY_CHARACTERISTIC_UUID
        handles_map[0xFF] = CasioConstants.SERIAL_NUMBER_STRING

        # GW-BX5600: SP_REQUEST (0x17) and SP_DATA (0x19)
        # Confirmed from btsnoop_hci_bx.log GATT discovery:
        handles_map[0x17] = CasioConstants.CASIO_SET_CONFIGURATION_CHARACTERISTIC_UUID
        handles_map[0x19] = CasioConstants.CASIO_GET_CONFIGURATION_CHARACTERISTIC_UUID
        
        return handles_map

    async def send_message(self, message: T) -> None:
        """Sends a message to the watch using the message dispatcher."""
        await message_dispatcher.MessageDispatcher.send_to_watch(message)
