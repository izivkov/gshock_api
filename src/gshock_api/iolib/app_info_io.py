from gshock_api.cancelable_result import CancelableResult
from gshock_api.iolib.actions import BLEAction, Write
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.iolib.packet import Header, Payload, Protocol, Trailer
from gshock_api.utils import to_hex_string


class AppInfoIOFunctional:
    """
    Pure functional app info modules implementing Monoids.
    """

    @staticmethod
    def prepare_watch_commands() -> list[BLEAction]:
        return [
            Write(
                handle=0x000C,
                data=bytes([Protocol.APP_INFO.value])
            )
        ]

    @staticmethod
    def prepare_watch_response(data: bytes) -> list[BLEAction]:
        if len(data) >= 12:
            try:
                protocol = Protocol(data[0])
                header = Header(protocol=protocol, size=len(data))
                payload = Payload(data=bytearray(data[1:11]))
                trailer = Trailer(data=bytearray(data[11:]), checksum=data[-1])

                if (header.protocol == Protocol.APP_INFO and
                    payload.data == bytearray([0xFF] * 10) and
                    trailer.data[0] == 0x00):

                    res_header = Header(protocol=Protocol.APP_INFO, size=12)
                    res_payload = Payload(data=bytearray.fromhex("3488F4E5D5AFC829E06D"))
                    res_trailer = Trailer(data=bytearray([0x02]), checksum=0x02)

                    packet_bytes = bytes([res_header.protocol.value]) + bytes(res_payload.data) + bytes(res_trailer.data)
                    return [Write(handle=0xE, data=packet_bytes)]
            except ValueError:
                pass
        return []


class AppInfoIO:
    """
    Stateful backward-compatible wrapper.
    Acts as the interpreter for AppInfoIOFunctional commands.
    """
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
        commands = AppInfoIOFunctional.prepare_watch_commands()
        for command in commands:
            if isinstance(command, Write):
                await connection.write(command.handle, command.data)

    @staticmethod
    def on_received(data: bytes) -> None:
        async def set_app_info(data_bytes: bytes) -> None:
            commands = AppInfoIOFunctional.prepare_watch_response(data_bytes)
            if commands:
                if AppInfoIO.connection is None:
                    raise RuntimeError("AppInfoIO.connection is not set")
                for command in commands:
                    if isinstance(command, Write):
                        await AppInfoIO.connection.write(command.handle, to_hex_string(command.data))

            if AppInfoIO.result is None:
                raise RuntimeError("AppInfoIO.result is not set")
            AppInfoIO.result.set_result("OK")

        import asyncio
        asyncio.create_task(set_app_info(data))
