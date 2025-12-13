from gshock_api.cancelable_result import CancelableResult
from gshock_api.utils import clean_str, to_ascii_string, to_hex_string
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.iolib.packet import Header, Protocol

class WatchNameIO:
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
        hex_str = to_hex_string(data)
        ascii_str = to_ascii_string(hex_str, 1)
        clean_data = clean_str(ascii_str)
        if WatchNameIO.result is None:
            raise RuntimeError("WatchNameIO.result is not set")
        WatchNameIO.result.set_result(clean_data)

    @staticmethod
    async def send_to_watch() -> None:
        pass
