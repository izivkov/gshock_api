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
T = TypeVar("T")

# Define a type for the watch filter function.
WatchFilter = Callable[[Any], bool] | None
Device = Any | None


class Connection:
    """Manages the BLE connection to a G-Shock watch using Bleak."""

    HandleMap = dict[int, str]

    def __init__(self, address: str | None = None) -> None:
        self.handles_map: Connection.HandleMap = self.init_handles_map()
        self.address: str | None = address
        self.client: BleakClient | None = None
        # Map UUID -> BleakGATTCharacteristic for discovered characteristics
        self.characteristics_map: dict[str, BleakGATTCharacteristic] = {}
        # Track which handles we've enabled notifications for to avoid duplicates
        self._notified_handles: set[int] = set()

    def notification_handler(
        self, characteristic: BleakGATTCharacteristic, data: bytearray  # noqa: ARG002
    ) -> None:
        message_dispatcher.MessageDispatcher.on_received(data)

    async def init_characteristics_map(self) -> None:
        """Populate `characteristics_map` with discovered Bleak characteristics."""
        if self.client is None:
            return

        services = self.client.services
        for service in services:
            for char in service.characteristics:
                logger.info(f"Characteristics: {char.uuid}")
                # Store the full BleakGATTCharacteristic so callers can inspect properties
                self.characteristics_map[char.uuid] = char

    async def connect(self, watch_filter: WatchFilter = None) -> bool:
        """Connect to the watch and subscribe to any characteristics that support notifications."""
        try:
            if self.address is None:
                device: Device = await scanner.scan(
                    device_address=self.address, watch_filter=watch_filter
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

            # Some Bleak backends require an explicit service discovery call
            try:
                await self.client.get_services()
            except Exception as e:
                logger.debug("client.get_services() failed or unnecessary on this backend", exc_info=True)

            try:
                await self.init_characteristics_map()
            except Exception:
                # Let outer except log full traceback and return False
                raise

            # Subscribe only to characteristics that advertise notify/indicate
            for uuid, char in self.characteristics_map.items():
                props = getattr(char, "properties", []) or []
                if "notify" in props or "indicate" in props:
                    try:
                        await self.client.start_notify(uuid, self.notification_handler)
                        # mark any mapped handle(s) for this uuid as notified
                        for h, u in self.handles_map.items():
                            if u == uuid:
                                self._notified_handles.add(h)
                    except Exception:
                        logger.debug(f"start_notify failed for {uuid}, ignoring")

            return True

        except Exception as e:
            logger.exception(f"[GShock Connect] Connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        if self.client and self.client.is_connected:
            await self.client.disconnect()

    def is_service_supported(self, handle: int) -> bool:
        uuid: str | None = self.handles_map.get(handle)
        return uuid is not None and uuid in self.characteristics_map

    async def write(self, handle: int, data: bytes | str) -> None:
        try:
            uuid: str | None = self.handles_map.get(handle)

            if uuid is None or uuid not in self.characteristics_map:
                logger.debug(f"write skipped: handle {handle} not in characteristics map")
                if handle == CasioConstants.HANDLE_ALL_FEATURES_NOTIFICATION:
                    logger.debug("Your watch does not support notifications...")
                return

            response_type: bool = handle == CasioConstants.HANDLE_ALL_FEATURES_WRITE

            if isinstance(data, bytes):
                cmd_data = data
            else:
                cmd_data = to_casio_cmd(data)

            if self.client:
                await self.client.write_gatt_char(uuid, cmd_data, response=response_type)

        except Exception as e:
            e.args = (type(e).__name__,)
            if isinstance(e, (BleakDBusError, EOFError)):
                raise GShockIgnorableException(e) from e
            raise GShockConnectionError(f"Unable to send time to watch: {e}") from e

    async def request(self, request: T) -> None:
        await self.write(0x0C, request)

    async def start_notify(
        self,
        handle: int,
        callback: Callable[[BleakGATTCharacteristic, bytearray], None],
    ) -> None:
        """Idempotent: start notifications for a mapped handle if available."""
        if handle in self._notified_handles:
            return

        uuid: str | None = self.handles_map.get(handle)
        if uuid is None or uuid not in self.characteristics_map or self.client is None:
            logger.debug(f"start_notify skipped: handle {handle} not in characteristics map")
            return

        await self.client.start_notify(uuid, callback)
        self._notified_handles.add(handle)

    def init_handles_map(self) -> dict[int, str]:
        handles_map: dict[int, str] = {}

        handles_map[CasioConstants.HANDLE_DEVICE_NAME_LEGACY] = CasioConstants.CASIO_GET_DEVICE_NAME
        handles_map[CasioConstants.HANDLE_APPEARANCE] = CasioConstants.CASIO_APPEARANCE
        handles_map[CasioConstants.HANDLE_TX_POWER] = CasioConstants.TX_POWER_LEVEL_CHARACTERISTIC_UUID

        handles_map[CasioConstants.HANDLE_READ_ALL_FEATURES] = CasioConstants.CASIO_READ_REQUEST_FOR_ALL_FEATURES_CHARACTERISTIC_UUID
        handles_map[CasioConstants.HANDLE_ALL_FEATURES_NOTIFICATION] = CasioConstants.CASIO_NOTIFICATION_CHARACTERISTIC_UUID
        handles_map[CasioConstants.HANDLE_ALL_FEATURES_WRITE] = CasioConstants.CASIO_ALL_FEATURES_CHARACTERISTIC_UUID

        handles_map[CasioConstants.HANDLE_DEVICE_NAME_GW] = CasioConstants.CASIO_GET_DEVICE_NAME
        handles_map[CasioConstants.HANDLE_ALL_FEATURES_WRITE] = CasioConstants.CASIO_ALL_FEATURES_CHARACTERISTIC_UUID
        handles_map[CasioConstants.HANDLE_CONFIG_WRITE] = CasioConstants.CASIO_SET_CONFIGURATION_CHARACTERISTIC_UUID
        handles_map[CasioConstants.HANDLE_CONFIG_NOTIFY] = CasioConstants.CASIO_GET_CONFIGURATION_CHARACTERISTIC_UUID

        handles_map[CasioConstants.HANDLE_DATA_REQUEST_SP] = CasioConstants.CASIO_DATA_REQUEST_SP_CHARACTERISTIC_UUID
        handles_map[CasioConstants.HANDLE_CONVOY_NOTIFICATION] = CasioConstants.CASIO_CONVOY_CHARACTERISTIC_UUID

        return handles_map

    async def send_message(self, message: T) -> None:
        await message_dispatcher.MessageDispatcher.send_to_watch(message)
