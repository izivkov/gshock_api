"""
home_time_io.py — HomeTime I/O.

A thin wrapper around WorldCitiesIO that reads a city slot and parses
the raw bytes into an ASCII city name string.

Slot 0 → main (home) city.
Slot 1 → secondary city (used by watches with a second dial, e.g. MTG-B1000).
"""

from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.iolib.world_cities_io import WorldCitiesIO


class HomeTimeIOFunctional:
    """
    Pure functional core for HomeTime processing.
    """

    @staticmethod
    def parse_home_city(data: bytes) -> str:
        """
        Skip the first 2 header bytes, decode the remainder as ASCII,
        and strip any null terminator — mirrors Kotlin's toAsciiString(data, 2).
        """
        return data[2:].split(b'\x00')[0].decode('ascii', errors='replace')


class HomeTimeIO:
    """
    Stateful wrapper for HomeTime reads.
    Delegates the actual BLE read to WorldCitiesIO and parses the result.
    """

    @staticmethod
    async def send_to_watch(_message: str = "") -> None:
        """
        Initiate a HomeTime read by delegating to WorldCitiesIO.
        Slot 0 = home/main city.
        """
        await WorldCitiesIO.send_to_watch(_message)

    @staticmethod
    def on_received(data: bytes) -> None:
        """
        Forward to WorldCitiesIO — HomeTime data arrives on a separate
        characteristic but is structurally identical to world cities data.
        """
        WorldCitiesIO.on_received(data)

    @staticmethod
    async def request(connection: ConnectionProtocol, slot: int = 0) -> str:
        """
        Read the city name for the given slot from the watch.

        Args:
            connection: Active BLE connection to the watch.
            slot: City slot to read (0 = home/main city, 1 = secondary city).

        Returns:
            ASCII city name string.
        """
        raw = await WorldCitiesIO.request(connection, slot)
        return HomeTimeIOFunctional.parse_home_city(raw)