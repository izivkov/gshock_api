import asyncio
from collections.abc import Sequence
from datetime import datetime
import sys

from args import args

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

            fine_adjustment_secs = args.get().fine_adjustment_secs
            await api.set_time(offset=fine_adjustment_secs)

            logger.info(f"Time set at {datetime.now()} on {watch_info.name}")

            if not watch_info.alwaysConnected:
                await connection.disconnect()

        except GShockConnectionError as e:
            logger.error(f"Got error: {e}")
            continue


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
