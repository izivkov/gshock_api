from collections.abc import Callable
from typing import Any, TypeVar
import asyncio
import subprocess

from bleak import BleakClient, BLEDevice
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

    # Only subscribe to notifications for known Casio UUIDs.
    # Subscribing to health-module or unknown UUIDs (e.g. DW-H5600 activity
    # service) causes the watch to drop the connection during setup.
    NOTIFY_WHITELIST: frozenset[str] = frozenset({
        CasioConstants.CASIO_NOTIFICATION_CHARACTERISTIC_UUID,
        CasioConstants.CASIO_ALL_FEATURES_CHARACTERISTIC_UUID,
        CasioConstants.CASIO_GET_CONFIGURATION_CHARACTERISTIC_UUID,
        CasioConstants.CASIO_CONVOY_CHARACTERISTIC_UUID,
    })

    def __init__(self, address: str | None = None) -> None:
        self.handles_map: Connection.HandleMap = self.init_handles_map()
        self.address: str | None = address
        self.device: BLEDevice | None = None
        self.client: BleakClient | None = None
        self.characteristics_map: dict[str, BleakGATTCharacteristic] = {}
        self._notified_handles: set[int] = set()

    def notification_handler(
        self, characteristic: BleakGATTCharacteristic, data: bytearray  # noqa: ARG002
    ) -> None:
        message_dispatcher.MessageDispatcher.on_received(data)

    async def init_characteristics_map(self) -> None:
        """Populate characteristics_map with discovered Bleak characteristics."""
        if self.client is None:
            return

        services = self.client.services
        for service in services:
            logger.info(f"Service: {service.uuid}")
            for char in service.characteristics:
                uuid_str = str(char.uuid).lower()
                logger.info(f"  Characteristic: {uuid_str} properties={getattr(char, 'properties', None)}")
                self.characteristics_map[uuid_str] = char

        # Diagnostic: log discovered vs expected UUIDs to help identify
        # watch-specific GATT layouts (e.g. DW-H5600 health service UUIDs)
        mapped_uuids = set(self.handles_map.values())
        discovered_uuids = set(self.characteristics_map.keys())
        missing = mapped_uuids - discovered_uuids
        extra = discovered_uuids - mapped_uuids
        if missing:
            logger.warning(f"Expected UUIDs not found on watch: {missing}")
        if extra:
            logger.info(f"Watch advertises additional UUIDs not in handles_map: {extra}")

    async def connect(self, watch_filter: WatchFilter = None) -> bool:
        try:
            if self.address is None:
                device: Device = await scanner.scan(
                    device_address=self.address, watch_filter=watch_filter
                )
                if device is None:
                    logger.info("No G-Shock device found.")
                    return False
                self.device = device
                self.address = device.address

            if self.address is None:
                return False

            client_target = self.device if self.device is not None else self.address
            self.client = BleakClient(client_target, timeout=30)

            # Attempt standard connect first (works for most watches)
            connected = False
            try:
                await self.client.connect(dangerous_use_bleak_cache=False)
                connected = self.client.is_connected
            except Exception as e:
                logger.warning(f"Standard connect failed ({e}), trying bluetoothctl handoff...")

            # Fallback for watches like DW-H5600 that drop during service discovery:
            # Keep bluetoothctl holding the connection open while Bleak attaches.
            if not connected:
                btctl_proc = await self._bluez_start_connection(self.address)
                if btctl_proc is None:
                    return False
                try:
                    # Bleak attaches to the already-connected device.
                    # Cache=True so it reads services BlueZ already resolved
                    # rather than triggering a second discovery round.
                    self.client = BleakClient(client_target, timeout=30)
                    await self.client.connect(dangerous_use_bleak_cache=True)
                    connected = self.client.is_connected
                finally:
                    # Now safe to let bluetoothctl go — Bleak owns the connection
                    await self._bluez_stop_connection(btctl_proc)

            if not connected:
                logger.info(f"Failed to connect to {self.address}")
                return False

            await asyncio.sleep(0.5)

            try:
                await self.init_characteristics_map()
            except Exception:
                raise

            for uuid, char in self.characteristics_map.items():
                if uuid not in self.NOTIFY_WHITELIST:
                    logger.debug(f"Skipping notify for non-whitelisted UUID: {uuid}")
                    continue
                props = getattr(char, "properties", []) or []
                if "notify" in props or "indicate" in props:
                    try:
                        await self.client.start_notify(uuid, self.notification_handler)
                        for h, u in self.handles_map.items():
                            if u == uuid:
                                self._notified_handles.add(h)
                    except Exception:
                        logger.debug(f"start_notify failed for {uuid}, ignoring")

            return True

        except Exception as e:
            logger.exception(f"[GShock Connect] Connection failed: {e}")
            return False


    async def _bluez_start_connection(self, address: str) -> asyncio.subprocess.Process | None:
        """
        Start bluetoothctl and hold the BLE connection open.
        Returns the live process — caller must call _bluez_stop_connection()
        after Bleak has successfully connected.
        """
        logger.info(f"bluetoothctl handoff connect: {address}")
        try:
            proc = await asyncio.create_subprocess_exec(
                "bluetoothctl",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            proc.stdin.write(f"connect {address}\n".encode())
            await proc.stdin.drain()

            # Wait for confirmed connection
            deadline = asyncio.get_event_loop().time() + 15
            connected = False
            while asyncio.get_event_loop().time() < deadline:
                try:
                    line = await asyncio.wait_for(proc.stdout.readline(), timeout=1.0)
                    text = line.decode()
                    logger.debug(f"bluetoothctl: {text.strip()}")
                    if "Connection successful" in text or "Connected: yes" in text:
                        connected = True
                        break
                except asyncio.TimeoutError:
                    continue

            if not connected:
                logger.warning("bluetoothctl did not confirm connection")
                await self._bluez_stop_connection(proc)
                return None

            # Give BlueZ a moment to resolve the service table
            await asyncio.sleep(1.0)
            logger.info("bluetoothctl holding connection — Bleak handoff starting")
            return proc  # caller keeps this alive until Bleak connects

        except Exception as e:
            logger.warning(f"bluetoothctl start failed: {e}")
            return None


    async def _bluez_stop_connection(self, proc: asyncio.subprocess.Process) -> None:
        """Cleanly exit bluetoothctl after Bleak has taken over the connection."""
        try:
            proc.stdin.write(b"quit\n")
            await proc.stdin.drain()
            await asyncio.wait_for(proc.wait(), timeout=3.0)
            logger.debug("bluetoothctl exited cleanly")
        except Exception as e:
            logger.debug(f"bluetoothctl exit: {e}")
            proc.kill()

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
