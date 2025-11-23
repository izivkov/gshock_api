from typing import Optional, Protocol

from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.utils import to_compact_string, to_hex_string


CHARACTERISTICS: dict[str, int] = CasioConstants.CHARACTERISTICS


class ConnectionProtocol(Protocol):
    async def request(self, code: str) -> None:
        ...

    def write(self, handle: int, data: bytes | str) -> None:
        ...


class AppInfoIO:
    result: Optional[CancelableResult[str]] = None
    connection: Optional[ConnectionProtocol] = None

    @staticmethod
    async def request(connection: ConnectionProtocol) -> CancelableResult[str]:
        AppInfoIO.connection = connection
        await connection.request("22")
        AppInfoIO.result = CancelableResult[str]()
        return await AppInfoIO.result.get_result()

    @staticmethod
    async def send_to_watch(connection: ConnectionProtocol) -> None:
        await connection.write(0x000C, bytearray([CHARACTERISTICS["CASIO_APP_INFORMATION"]]))

    @staticmethod
    def on_received(data: bytes) -> None:
        def set_app_info(data_str: str) -> None:
            # App info needed to re-enable button D after reset/CLEARED BLE.
            app_info_compact_str = to_compact_string(data_str)
            if app_info_compact_str == "22FFFFFFFFFFFFFFFFFFFF00":
                if AppInfoIO.connection is None:
                    raise RuntimeError("AppInfoIO.connection is not set")
                AppInfoIO.connection.write(0xE, "223488F4E5D5AFC829E06D02")

        set_app_info(to_hex_string(data))
        if AppInfoIO.result is None:
            raise RuntimeError("AppInfoIO.result is not set")
        AppInfoIO.result.set_result("OK")
