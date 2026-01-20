from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.iolib.packet import Header, Protocol
from gshock_api.pending_requests_registry import PendingRequestsRegistry

CHARACTERISTICS: dict[str, int] = CasioConstants.CHARACTERISTICS


class DstForWorldCitiesIO:
    result: CancelableResult = None
    connection = None

    @staticmethod
    async def request(connection: ConnectionProtocol, city_number: int) -> CancelableResult[bytes]:
        DstForWorldCitiesIO.connection = connection
        key = f"{Protocol.DST_SETTING.value:02x}0{city_number}"
        await connection.request(key)

        DstForWorldCitiesIO.result = CancelableResult()
        # Register the pending request with unique name based on city number
        PendingRequestsRegistry.register(f"DstForWorldCitiesIO_{city_number}", DstForWorldCitiesIO.result)
        try:
            return await DstForWorldCitiesIO.result.get_result()
        finally:
            # Unregister when complete (success or error)
            PendingRequestsRegistry.unregister(f"DstForWorldCitiesIO_{city_number}")

    @staticmethod
    async def send_to_watch(connection: ConnectionProtocol) -> None:
        header = Header(Protocol.DST_SETTING, size=1)
        await connection.write(0x000C, bytearray([header.protocol.value]))

    @staticmethod
    def on_received(data: bytes) -> None:
        if DstForWorldCitiesIO.result is None:
            raise RuntimeError("DstForWorldCitiesIO.result is not set")
        DstForWorldCitiesIO.result.set_result(data)
