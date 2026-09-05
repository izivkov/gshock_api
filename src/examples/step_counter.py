"""
Step counter example

Demonstrates the step-counter methods on GshockAPI:
    - get_step_summary(): quick call, returns today's total step count as an int.
    - get_step_count(peek=True): full step-counter data (hourly + daily
      history) as a StepCounterData.

peek=True is passed explicitly (rather than relying on the library default of
peek=False) so the transaction is left open and the watch does NOT clear its
lifelog buffers - this script only inspects data, it should not erase it.
(get_step_history() is not shown separately: it is get_step_count(peek=True)
under the hood - same underlying call, same result.)

Note: get_step_summary() has no peek option - it always closes the
transaction, so it may clear the watch's hourly buffer regardless.

Connects to a paired watch, calls each method in turn, and prints the results.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gshock_api.connection import Connection
from gshock_api.exceptions import GShockConnectionError
from gshock_api.gshock_api import GshockAPI
from gshock_api.logger import logger


async def main() -> None:
    logger.info("Press and hold lower-left button on your watch for 3 seconds to pair...")
    logger.info("Press lower-right button once if already paired.")

    connection = Connection()
    connected = await connection.connect(watch_filter=None)
    if not connected:
        raise GShockConnectionError("Failed to find or connect to the watch.")
    logger.info("Connected...")

    api = GshockAPI(connection)

    watch_name = await api.get_watch_name()
    logger.info(f"Watch name: {watch_name}")

    total_steps = await api.get_step_summary()
    print(f"\nget_step_summary() -> {total_steps} steps today")

    step_data = await api.get_step_count(peek=True)
    print("\nget_step_count(peek=True) ->")
    print(f"  current_day_steps: {step_data.current_day_steps}")
    print(f"  timestamp: {step_data.timestamp}")
    print(f"  distance_meters: {step_data.distance_meters}")
    print(f"  hourly_steps: {step_data.hourly_steps}")
    print(f"  daily_history: {step_data.daily_history}")
    if step_data.warnings:
        print(f"  warnings: {step_data.warnings}")

    await connection.disconnect()
    logger.info("Disconnected.")


if __name__ == "__main__":
    asyncio.run(main())