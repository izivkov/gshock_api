from gshock_api.cancelable_result import CancelableResult
from gshock_api.iolib.actions import BLEAction, Write
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.iolib.packet import Protocol
from gshock_api.utils import clean_str, to_ascii_string, to_hex_string


class WatchNameIOFunctional:
    """
    Pure functional watch name modules implementing Monoids.
    """

    @staticmethod
    def decode(data_bytes: bytes) -> str:
        hex_str = to_hex_string(data_bytes)
        ascii_str = to_ascii_string(hex_str, 1)
        return clean_str(ascii_str)

    @staticmethod
    def prepare_watch_commands() -> list[BLEAction]:
        return [
            Write(
                handle=0x000C,
                data=bytes([Protocol.WATCH_NAME.value])
            )
        ]


class WatchNameIO:
    """
    Stateful backward-compatible wrapper.
    Acts as the interpreter for WatchNameIOFunctional commands.
    """
    result: CancelableResult | None = None
    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol) -> str | None:
        WatchNameIO.connection = connection
        await connection.request(f"{Protocol.WATCH_NAME.value:02X}")
        WatchNameIO.result = CancelableResult[str]()
        return await WatchNameIO.result.get_result()

    @staticmethod
    def on_received(data: bytes) -> None:
        clean_data = WatchNameIOFunctional.decode(data)
        if WatchNameIO.result is None:
            raise RuntimeError("WatchNameIO.result is not set")
        WatchNameIO.result.set_result(clean_data)

    @staticmethod
    async def send_to_watch() -> None:
        pass
