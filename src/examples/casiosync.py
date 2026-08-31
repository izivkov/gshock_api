import asyncio
import argparse
import base64
import datetime
import logging
import zlib
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent / 'gshock_api/src'))

from gshock_api.connection import Connection
from gshock_api.exceptions import GShockConnectionError
from gshock_api.gshock_api import GshockAPI
from gshock_api.logger import logger


async def _fetch_lifelog(api: GshockAPI, *, peek: bool, print_log: bool) -> None:
    """Fetch lifelog from the watch, parse it, and optionally emit log lines."""
    from gshock_api.iolib.lifelog_io import LifelogIO
    from lifelog import Lifelog

    steps = await api.get_lifelog_steps(peek=peek)
    logger.info(f"Total steps: {steps}")

    log = Lifelog.parse(LifelogIO._buffer)
    logger.info(f"parsed lifelog: {log.total_steps} steps, {log.total_distance}m")

    if not print_log:
        return

    raw = base64.b64encode(zlib.compress(LifelogIO._buffer)).decode()
    print(f'lifelog buffer="{raw}"')

    for entry in log.lifelog_entries():
        parts = [
            f'lifelog time="{entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")}"',
            f'steps="{entry.steps}"',
        ]
        if entry.intensity:
            parts.append(f'intensity="{",".join(map(str, entry.intensity))}"')
        if entry.approx:
            parts.append("approx")
        if entry.pending:
            parts.append("pending")
        print(" ".join(parts))


async def main() -> None:
    parser = argparse.ArgumentParser(description="Sync G-Shock lifelog data.")
    parser.add_argument("--addr", type=str, help="MAC address of the watch to connect to directly")
    parser.add_argument("--timeout", type=float, default=-1.0, help="Connection timeout in seconds (-1 for infinite)")
    parser.add_argument("--peek", action="store_true", help="Fetch lifelog without clearing the watch's hourly buffer")
    parser.add_argument("--log", action="store_true", help="Print the lifelog in a structured log format to stdout")
    parser.add_argument("--quiet", action="store_true", help="Reduce log output on stderr (only print errors)")
    args = parser.parse_args()

    if args.quiet:
        logging.getLogger('gshock_api').setLevel(logging.ERROR)
        logging.getLogger('bleak').setLevel(logging.ERROR)

    logger.info("=======================================================================")
    logger.info("Press and hold lower-left button on your watch for 3 seconds to pair...")
    logger.info("            Press lower-right button once if already paired.           ")
    logger.info("    At 00:30, 06:30, 12:30, or 18:30, a paired watch may auto sync.    ")
    logger.info("=======================================================================")
    logger.info("")

    try:
        logger.info("Waiting for connection...")

        if args.addr:
            logger.info(f"Using specific MAC address: {args.addr}")

        connection = Connection(address=args.addr)

        # Convert -1.0 to sys.float_info.max for infinite timeout
        timeout = sys.float_info.max if args.timeout == -1.0 else args.timeout
        connected = await connection.connect(watch_filter=None, timeout=timeout)
        if not connected:
            raise GShockConnectionError("Failed to find or connect to the watch before timeout.")

        logger.info("Connected...")

        api = GshockAPI(connection)

        watch_name = await api.get_watch_name()
        logger.info(f"got watch name: {watch_name}")

        # Lifelog must come before set_time in all modes because
        # set_time → initialize_for_setting_time() kills 0x11 writability.
        try:
            await _fetch_lifelog(api, peek=args.peek, print_log=args.log)
        except Exception as e:
            logger.warning(f"Lifelog fetch failed: {e}")

        logger.info("Syncing time...")
        await api.set_time()

    except GShockConnectionError as e:
        logger.error(f"Connection problem: {e}")
        sys.exit(1)

    await connection.disconnect()
    logger.info("disconnected")


if __name__ == "__main__":
    asyncio.run(main())
