import asyncio
import sys

from datetime import datetime
import time

from gshock_api.connection import Connection
from gshock_api.gshock_api import GshockAPI
from gshock_api.iolib.button_pressed_io import WatchButton
from gshock_api.scanner import scanner
from gshock_api.configurator import conf
from gshock_api.logger import logger
from gshock_api.watch_info import watch_info
from args import args
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
    prompt()

    while True:
        try:
            address = None

            logger.info(f"Waiting for connection...")
            connection = Connection(address)
            await connection.connect()
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
            logger.info(f"Watch name: {watch_name}")

            # Apply fine adjustment to the time
            fine_adjustment_secs = args.get().fine_adjustment_secs
            await api.set_time(int(time.time()) + fine_adjustment_secs)
            logger.info(f"Time set at {datetime.now()} on {watch_info.name}")

            # Only update the display of we have pressed LOWER-LEFT button,
            # Otherwise the watch will dicoinnect before we get all the information for the display.
            # if pressed_button == WatchButton.LOWER_LEFT:
            #     await show_display(api)

            if watch_info.alwaysConnected == False:
                await connection.disconnect()

        except Exception as e:
            logger.error(f"Got error: {e}")
            continue


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
