import asyncio
from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from gshock_api.casio_constants import CasioConstants
from gshock_api import message_dispatcher
from gshock_api.utils import to_casio_cmd
from gshock_api.logger import logger

class Connection:
    def __init__(self, device):
        self.handles_map = self.init_handles_map()
        self.device = device
        self.client = BleakClient(device)
        self.characteristics_map = {}

    def notification_handler(
        self, characteristic: BleakGATTCharacteristic, data: bytearray
    ):
        message_dispatcher.MessageDispatcher.on_received(data)

    async def init_characteristics_map(self):
        """
        Prints all services and characteristics of the connected BLE device.
        """
        services = await self.client.get_services()
        print(f"got services...")
        for service in services:
            for char in service.characteristics:
                self.characteristics_map[char.uuid] = char.uuid  # Store in map

    async def connect(self):
        try:
            await self.client.connect()
            await self.init_characteristics_map()
            await self.client.start_notify(
                CasioConstants.CASIO_ALL_FEATURES_CHARACTERISTIC_UUID,
                self.notification_handler,
            )
            return True
        except Exception as e:
            logger.debug(f"Cannot connect: {e}")
            return False

    async def disconnect(self):
        await self.client.disconnect()

    def is_service_supported(self, handle):
        uuid = self.handles_map.get(handle)
        supported = (uuid not in self.characteristics_map)
        print(f"write, service with handle {handle} is supported: {supported}")
        return supported

    async def write(self, handle, data):
        try:
            uuid = self.handles_map.get(handle)
            if (uuid not in self.characteristics_map):
                logger.error(
                    "write failed: handle {} not in characteristics map".format(handle)
                )
                if (handle == 13):
                    logger.error(
                        "Your watch does not suppot notifications..."
                    )
                return
            
            await self.client.write_gatt_char(
                uuid, to_casio_cmd(data)
            )
        except Exception as e:
            logger.debug("write failed with exception: {}".format(e))

    async def request(self, request):
        logger.info("write: {}".format(request))
        await self.write(0xC, request)

    def init_handles_map(self):
        handles_map = {}

        handles_map[0x04] = CasioConstants.CASIO_GET_DEVICE_NAME
        handles_map[0x06] = CasioConstants.CASIO_APPEARANCE
        handles_map[0x09] = CasioConstants.TX_POWER_LEVEL_CHARACTERISTIC_UUID
        handles_map[
            0x0C
        ] = CasioConstants.CASIO_READ_REQUEST_FOR_ALL_FEATURES_CHARACTERISTIC_UUID
        handles_map[0x0E] = CasioConstants.CASIO_ALL_FEATURES_CHARACTERISTIC_UUID
        handles_map[0x0D] = CasioConstants.CASIO_NOTIFICATION_CHARACTERISTIC_UUID
        handles_map[0x11] = CasioConstants.CASIO_DATA_REQUEST_SP_CHARACTERISTIC_UUID
        handles_map[0x14] = CasioConstants.CASIO_CONVOY_CHARACTERISTIC_UUID
        handles_map[0xFF] = CasioConstants.SERIAL_NUMBER_STRING

        return handles_map

    async def sendMessage(self, message):
        await message_dispatcher.MessageDispatcher.send_to_watch(message)
