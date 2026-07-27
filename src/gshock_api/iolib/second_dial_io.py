"""
MTG-B1000 dual-dial time-set implementation.

The MTG-B1000 is identical to the standard G-Shock time protocol for the
main dial, plus a second-dial sequence bracketed by ResetSequence commands.

Protocol confirmed from btsnoop_hci_mgt_b1000.log:

  ── Main dial ───────────────────────────────────────────────────────────
  Identical to standard watches — handled entirely by existing IO classes
  via the normal SET_TIME dispatch path.

  ── Second dial ─────────────────────────────────────────────────────────
  [1758] WRITE 210001        ResetSequence start (dial=0)
  [1763] READ  0x1d          DstWatchStateIO.request(state=ZERO)
  [1766] WRITE 0x1d          DstWatchStateIO.send_to_watch()
  [1769] READ  0x1e city 0   DstForWorldCitiesIO.request(city_number=0)
  [1774] READ  0x1e city 1   DstForWorldCitiesIO.request(city_number=1)
  [1777] WRITE 0x1e city 0   DstForWorldCitiesIO echo write-back
  [1780] WRITE 0x1e city 1   DstForWorldCitiesIO echo write-back
  [1783] READ  0x1f city 0   WorldCitiesIO.request(city_number=0)
  [1787] READ  0x1f city 1   WorldCitiesIO.request(city_number=1)
  [1783] WRITE 0x24 city 0   WorldCitiesIO echo write-back
  [1787] WRITE 0x24 city 1   WorldCitiesIO echo write-back
  [1793] WRITE 210101        ResetSequence end (dial=1)

ResetSequence byte format: 21 {dial_index} 01
"""

from typing import ClassVar

from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.iolib.dst_for_world_cities_io import DstForWorldCitiesIO
from gshock_api.iolib.dst_watch_state_io import DstWatchStateIO, DtsState
from gshock_api.iolib.world_cities_io import WorldCitiesIO
from gshock_api.logger import logger
from gshock_api.watch_info import watch_info

HANDLE_WRITE = 0x000E   # write-with-response (SET)

# ResetSequence commands confirmed from log [1758] and [1793]
RESET_SEQUENCE_START = bytes([0x21, 0x00, 0x01])   # dial 0
RESET_SEQUENCE_END   = bytes([0x21, 0x01, 0x01])   # dial 1


class SecondDialIO:
    """Sets the time on the Second Dial, including the second analogue dial.

    The main dial time set is handled by the normal SET_TIME dispatch path
    (TimeIO) — no duplication needed here.  This class only implements the
    additional second-dial sequence that the Second Dial requires after the
    main time command.
    """

    connection: ClassVar[ConnectionProtocol | None] = None

    # ── Public entry point ────────────────────────────────────────────────────

    @staticmethod
    async def set_second_dial(connection: ConnectionProtocol) -> None:
        """Run the second-dial sequence after the main time has been set.

        Call this immediately after the standard SET_TIME command completes.
        Reads current DST, city, and world-city data from the watch, then
        writes them back bracketed by ResetSequence commands so the second
        analogue dial syncs to the second world city.
        """
        SecondDialIO.connection = connection
        logger.info("SecondDialIO: starting second dial sequence")

        # ResetSequence start
        await connection.write(HANDLE_WRITE, RESET_SEQUENCE_START)
        logger.info("ResetSequence start (210001)")

        # Read and write back DST watch state (0x1d)
        dst_data = await DstWatchStateIO.request(connection, DtsState.ZERO)
        await connection.write(HANDLE_WRITE, dst_data)

        # Read and write back DST city settings (0x1e) for both cities
        dst_city0 = await DstForWorldCitiesIO.request(connection, city_number=0)
        dst_city1 = await DstForWorldCitiesIO.request(connection, city_number=1)
        await connection.write(HANDLE_WRITE, dst_city0)
        await connection.write(HANDLE_WRITE, dst_city1)

        if watch_info.hasWorldCities:
          # Read and write back world city coordinates (0x1f) for both cities
          wc0 = await WorldCitiesIO.request(connection, city_number=0)
          wc1 = await WorldCitiesIO.request(connection, city_number=1)
          await connection.write(HANDLE_WRITE, wc0)
          await connection.write(HANDLE_WRITE, wc1)

        # ResetSequence end
        await connection.write(HANDLE_WRITE, RESET_SEQUENCE_END)
        logger.info("ResetSequence end (210101)")

        logger.info("SecondDialIO: second dial sequence complete")
        