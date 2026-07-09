from gshock_api.cancelable_result import CancelableResult
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.iolib.world_cities_io import WorldCitiesIO
from gshock_api.utils import clean_str, to_ascii_string, to_hex_string


class HomeTimeIOFunctional:
    """Pure functional core for home time processing.

    All methods are stateless and side-effect free.
    """

    @staticmethod
    def parse_home_city(data: bytes) -> str:
        """Extract the home city name from raw world-cities data.

        The city name starts at byte index 2 (skipping the protocol
        header and city index byte), encoded as ASCII.
        """
        hex_str = to_hex_string(data)
        return clean_str(to_ascii_string(hex_str, 2))


class HomeTimeIO:
    """Stateful wrapper — reads home city name from world city slot 0.

    Follows the same pattern as WatchNameIO: a pure functional decode
    step inside on_received(), with CancelableResult for async delivery.
    """

    result: CancelableResult[str] | None = None
    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol) -> str:
        """Request the home city name (world city slot 0)."""
        HomeTimeIO.connection = connection
        HomeTimeIO.result = CancelableResult[str]()

        # WorldCitiesIO.request() sends the read command and waits for
        # the raw bytes response, which on_received() will decode.
        raw = await WorldCitiesIO.request(connection, city_number=0)
        return HomeTimeIOFunctional.parse_home_city(raw)

    @staticmethod
    def on_received(data: bytes) -> None:
        """Route incoming world-cities data to the pending result."""
        if HomeTimeIO.result is None:
            return
        home_city = HomeTimeIOFunctional.parse_home_city(data)
        HomeTimeIO.result.set_result(home_city)

    @staticmethod
    async def send_to_watch() -> None:
        pass