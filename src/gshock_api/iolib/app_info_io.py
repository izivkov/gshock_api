from typing import Optional, Protocol as TypingProtocol

from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.utils import to_compact_string, to_hex_string
from gshock_api.iolib.packet import Header, Payload, Trailer, Protocol
from gshock_api.iolib.connection_protocol import ConnectionProtocol

CHARACTERISTICS: dict[str, int] = CasioConstants.CHARACTERISTICS


class AppInfoIO:
    result: CancelableResult = None
    connection: ConnectionProtocol = None

    @staticmethod
    async def request(connection: ConnectionProtocol) -> CancelableResult[str]:
        AppInfoIO.connection = connection
        await connection.request(f"{Protocol.APP_INFO.value:02X}")
        AppInfoIO.result = CancelableResult[str]()
        return await AppInfoIO.result.get_result()

    @staticmethod
    async def send_to_watch(connection: ConnectionProtocol) -> None:
        header = Header(protocol=Protocol.APP_INFO, size=1)
        await connection.write(0x000C, bytearray([header.protocol.value]))

    @staticmethod
    def on_received(data: bytes) -> None:
        async def set_app_info(data_str: str) -> None:
            # Parse data into types
            # Expected: 22 (Header) + 10 bytes (Payload) + 00 (Trailer)
            if len(data) >= 12:
                try:
                    protocol = Protocol(data[0])
                    header = Header(protocol=protocol, size=len(data))
                    payload = Payload(data=bytearray(data[1:11]))
                    trailer = Trailer(data=bytearray(data[11:]), checksum=data[-1])
                    
                    # Logic: if app_info_compact_str == "22FFFFFFFFFFFFFFFFFFFF00":
                    if (header.protocol == Protocol.APP_INFO and 
                        payload.data == bytearray([0xFF] * 10) and 
                        trailer.data[0] == 0x00):
                        
                        if AppInfoIO.connection is None:
                            raise RuntimeError("AppInfoIO.connection is not set")
                        
                        # Construct response packet using types
                        # "223488F4E5D5AFC829E06D02"
                        res_header = Header(protocol=Protocol.APP_INFO, size=12)
                        res_payload = Payload(data=bytearray.fromhex("3488F4E5D5AFC829E06D"))
                        res_trailer = Trailer(data=bytearray([0x02]), checksum=0x02)
                        
                        packet_bytes = bytearray([res_header.protocol.value]) + res_payload.data + res_trailer.data
                        await AppInfoIO.connection.write(0xE, to_hex_string(packet_bytes))
                    
                except ValueError:
                    # Invalid protocol or data
                    pass
            
            if AppInfoIO.result is None:
                raise RuntimeError("AppInfoIO.result is not set")
            AppInfoIO.result.set_result("OK")

        import asyncio
        asyncio.create_task(set_app_info(to_hex_string(data)))
