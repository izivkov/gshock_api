from gshock_api.cancelable_result import CancelableResult
from gshock_api.iolib.actions import BLEAction, Write
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.iolib.packet import Protocol


class DstForWorldCitiesIOFunctional:
    """
    Pure functional DST for world cities modules implementing Monoids.
    """

    @staticmethod
    def prepare_watch_commands() -> list[BLEAction]:
        return [
            Write(
                handle=0x000C,
                data=bytes([Protocol.DST_SETTING.value])
            )
        ]


class DstForWorldCitiesIO:
    """
    Stateful backward-compatible wrapper.
    Acts as the interpreter for DstForWorldCitiesIOFunctional commands.
    """
    result: CancelableResult = None
    connection = None

    @staticmethod
    async def request(connection: ConnectionProtocol, city_number: int) -> CancelableResult[bytes]:
        DstForWorldCitiesIO.connection = connection
        key = f"{Protocol.DST_SETTING.value:02x}0{city_number}"
        await connection.request(key)

        DstForWorldCitiesIO.result = CancelableResult()
        return await DstForWorldCitiesIO.result.get_result()

    @staticmethod
    async def send_to_watch(connection: ConnectionProtocol) -> None:
        commands = DstForWorldCitiesIOFunctional.prepare_watch_commands()
        for command in commands:
            if isinstance(command, Write):
                await connection.write(command.handle, command.data)

    @staticmethod
    def on_received(data: bytes) -> None:
        if DstForWorldCitiesIO.result is None:
            raise RuntimeError("DstForWorldCitiesIO.result is not set")
        DstForWorldCitiesIO.result.set_result(data)
