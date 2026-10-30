"""DST transaction wrapper (opcode 0x21) used by F-B100W and related models.

Confirmed against full HCI captures of the official app:
  type 1: change world city
  type 2: swap home/world cities
  type 3: change home DST state (Summer Time screen)
"""
from enum import IntEnum

from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.iolib.packet import Protocol


class DstTransactionType(IntEnum):
    WORLD_CITY = 1
    SWAP_HOME_WORLD = 2
    DST_STATE = 3


class DstTransactionIO:
    """Begin/end a 0x21 transaction around the relevant 0x1D/0x1E writes."""

    @staticmethod
    def encode(command: int, transaction_type: DstTransactionType | int) -> bytes:
        return bytes([Protocol.DST_TRANSACTION.value, command, int(transaction_type)])

    @staticmethod
    async def begin(
        connection: ConnectionProtocol,
        transaction_type: DstTransactionType | int = DstTransactionType.WORLD_CITY,
    ) -> None:
        await connection.write(
            0x000E, DstTransactionIO.encode(0x00, transaction_type)
        )

    @staticmethod
    async def end(
        connection: ConnectionProtocol,
        transaction_type: DstTransactionType | int = DstTransactionType.WORLD_CITY,
    ) -> None:
        await connection.write(
            0x000E, DstTransactionIO.encode(0x01, transaction_type)
        )
