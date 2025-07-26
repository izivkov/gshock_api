import asyncio
import sys

from datetime import datetime
import time

from gshock_api.connection import Connection
from gshock_api.gshock_api import GshockAPI
from gshock_api.iolib.button_pressed_io import WatchButton
from gshock_api.scanner import scanner
from gshock_api.logger import logger
from gshock_api.watch_info import watch_info
from args import args
from gshock_api.exceptions import GShockConnectionError
import time


__author__ = "Ivo Zivkov"
__copyright__ = "Ivo Zivkov"
__license__ = "MIT"

async def main(argv):
    await run_time_server()

def prompt():
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

async def run_time_server():
    excluded_watches = ["DW-H5600", "OCW-S400", "OCW-S400SG", "OCW-T200SB", "ECB-30", "ECB-20", "ECB-10", "ECB-50", "ECB-60", "ECB-70"]

    prompt()

    while True:
        try:
            logger.info(f"Waiting for connection...")
            connection = Connection(address="E8:3E:76:AC:6A:35")
            await connection.connect(excluded_watches)
            logger.info(f"Connected...")

            api = GshockAPI(connection)
            pressed_button = await api.get_pressed_button()
            if (
                pressed_button != WatchButton.LOWER_RIGHT
                and pressed_button != WatchButton.NO_BUTTON
                and pressed_button != WatchButton.LOWER_LEFT
            ):
                continue

            watch_name = await api.get_watch_name()

            # Apply fine adjustment to the time
            fine_adjustment_secs = args.get().fine_adjustment_secs
            
            await api.set_time(offset=fine_adjustment_secs)
            logger.info(f"Time set at {datetime.now()} on {watch_info.name}")

            if watch_info.alwaysConnected == False:
                await connection.disconnect()

        except GShockConnectionError as e:
            logger.error(f"Got error: {e}")
            continue


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
