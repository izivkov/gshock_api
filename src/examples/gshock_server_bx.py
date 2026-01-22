import asyncio
from collections.abc import Sequence
from datetime import datetime
import sys

from gshock_api.always_connected_watch_filter import (
    always_connected_watch_filter as watch_filter,
)
from gshock_api.connection import Connection
from gshock_api.exceptions import GShockConnectionError
from gshock_api.gshock_api import GshockAPI
from gshock_api.iolib.button_pressed_io import WatchButton
from gshock_api.logger import logger
from gshock_api.watch_info import watch_info

__author__ = "Ivo Zivkov"
__copyright__ = "Ivo Zivkov"
__license__ = "MIT"


async def main(argv: Sequence[str]) -> None:
    await run_time_server()

def prompt() -> None:
    logger.info(
        "=============================================================================================="
    )
    logger.info("Short-press lower-right button on your watch to set time...")
    logger.info("")
    logger.info(
        "If Auto-time set on watch, the watch will connect and run automatically up to 4 times per day."
    )
    logger.info(
        "=============================================================================================="
    )
    logger.info("")


async def send_raw_command(connection: Connection, handle: int, hex_value: str) -> None:
    logger.info(f"Sending raw command: handle={handle:04X}, value={hex_value}")
    await connection.write(handle, hex_value)


async def run_gw_bx_sequence(connection: Connection):
    logger.info("Starting GW-BX5600 initialization sequence...")
    
    # 1. Base initialization
    # await send_raw_command(connection, 0x000C, "22")
    # await send_raw_command(connection, 0x000C, "10")
    
    # # 2. Echo Watch Name
    # await send_raw_command(connection, 0x000E, "23434153494F2047572D42583536303000000000")
    
    # # 3. Request Watch Info
    # await send_raw_command(connection, 0x000C, "26")
    # await send_raw_command(connection, 0x000C, "28")
    # await send_raw_command(connection, 0x000C, "20")
    # await asyncio.sleep(0.5)
    # await send_raw_command(connection, 0x000C, "28")
    # await send_raw_command(connection, 0x000C, "20")
    # await send_raw_command(connection, 0x000C, "28")
    
    # 4. DST / World Cities handshake (Replaying logs)
    # Commands on 0x17 usually trigger a response on 0x19 which is echoed back to 0x19
    # await send_raw_command(connection, 0x0017, "051D001D00240024012402")
    # await send_raw_command(connection, 0x0019, "020F001D000106065E761901FFFFFFFFFFFF0F001D020302000000FFFFFFFFFFFFFFFF")
    
    # await send_raw_command(connection, 0x0017, "031E001E001E00")
    # await send_raw_command(connection, 0x0019, "0607001E005E7620040007001E01190124040007001E02000000000014002400014036B9186DB50F41405C90B4916CA46E0314002401014041D841355475A3406176227D028A1E0214002402014049C0000000000000000000000000000000")
    
    # await send_raw_command(connection, 0x0017, "061F001F061F011F071F021F08")
    # await send_raw_command(connection, 0x0019, "0614001F005348414E474841490000000000000000000014001F0653484100000000000000000000000000000014001F01544F4B594F0000000000000000000000000014001F0754594F00000000000000000000000000000014001F0228555443290000000000000000000000000014001F08555443000000000000000000000000000000")
    
    # 5. Final Time Setting (Expected to set watch to 2026-01-10 00:30:35)
    # await send_raw_command(connection, 0x000E, "09EA07010A001E23060501")

    await send_raw_command(connection, 0x0017, "051D001D00240024012402")
    await send_raw_command(connection, 0x0019, "020F001D000106065E761901FFFFFFFFFFFF0F001D020302000000FFFFFFFFFFFFFFFF")
    await send_raw_command(connection, 0x0017, "031E001E001E00")
    await send_raw_command(connection, 0x0019, "0607001E005E7620040007001E01190124040007001E02000000000014002400014036B9173FB7A5F4405C90B5350092CD0314002401014041D841355475A3406176227D028A1E0214002402014049C00000000000000000000000000000")
    await send_raw_command(connection, 0x0017, "061F001F061F011F071F021F08")
    await send_raw_command(connection, 0x0019, "0614001F005348414E474841490000000000000000000014001F0653484100000000000000000000000000000014001F01544F4B594F0000000000000000000000000014001F0754594F00000000000000000000000000000014001F0228555443290000000000000000000000000014001F08555443000000000000000000000000000000")
    await send_raw_command(connection, 0x000E, "09EA070115161B03036801")

    logger.info("Sequence complete.")

async def run_time_server() -> None:
    prompt()

    while True:
        try:
            logger.info("Waiting for connection...")
            connection = Connection()
            await connection.connect(watch_filter.connection_filter)
            logger.info("Connected...")

            api = GshockAPI(connection)
            pressed_button = await api.get_pressed_button()
            if (
                pressed_button not in (WatchButton.LOWER_RIGHT, WatchButton.NO_BUTTON, WatchButton.LOWER_LEFT)
            ):
                continue

            name = await api.get_watch_name()
            logger.info(f"name: {name}")

            # Run specialized sequence for GW-BX5600
            await run_gw_bx_sequence(connection)

            logger.info(f"Time set at {datetime.now()} on {watch_info.name}")

            if not watch_info.alwaysConnected:
                await connection.disconnect()

        except GShockConnectionError as e:
            logger.error(f"Got error: {e}")
            continue


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
