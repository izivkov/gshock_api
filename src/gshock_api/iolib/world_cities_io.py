from gshock_api.cancelable_result import CancelableResult
from gshock_api.iolib.actions import BLEAction, Write
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.iolib.packet import Protocol


class WorldCitiesIOFunctional:
    """
    Pure functional world cities modules implementing Monoids.
    """

    @staticmethod
    def prepare_watch_commands() -> list[BLEAction]:
        return [
            Write(
                handle=0x000C,
                data=bytes([Protocol.WORLD_CITIES.value])
            )
        ]


class WorldCitiesIO:
    """
    Stateful backward-compatible wrapper.
    Acts as the interpreter for WorldCitiesIOFunctional commands.
    """
    result: CancelableResult[bytes] | None = None
    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol, city_number: int) -> CancelableResult[bytes]:
        WorldCitiesIO.connection = connection
        key = f"{Protocol.WORLD_CITIES.value:02X}0{city_number}"
        await connection.request(key)

        WorldCitiesIO.result = CancelableResult[bytes]()
        return await WorldCitiesIO.result.get_result()

    @staticmethod
    async def send_to_watch(connection: ConnectionProtocol) -> None:
        commands = WorldCitiesIOFunctional.prepare_watch_commands()
        for command in commands:
            if isinstance(command, Write):
                await connection.write(command.handle, command.data)

    @staticmethod
    def parse_city(time_zone_name: str) -> str:
        return time_zone_name.split("/")[-1].split(":")[-1].upper()

    @staticmethod
    def encode_and_pad(city_name: str, city_number: int) -> bytes:
        city_bytes = city_name.encode("ascii", errors="ignore")
        padded_bytes = bytearray(19)
        padded_bytes[0] = Protocol.WORLD_CITIES.value
        padded_bytes[1] = city_number

        for i, b in enumerate(city_bytes):
            if i + 2 < 19:
                padded_bytes[i + 2] = b
            else:
                break
        return bytes(padded_bytes)

    @staticmethod
    def on_received(data: bytes) -> None:
        if WorldCitiesIO.result is None:
            raise RuntimeError("WorldCitiesIO.result is not set")
        WorldCitiesIO.result.set_result(data)
