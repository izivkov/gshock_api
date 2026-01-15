import asyncio
from collections.abc import Sequence
from datetime import datetime
import json
from pprint import pformat
import sys
import time

import pytz

from gshock_api.always_connected_watch_filter import (
    always_connected_watch_filter as watch_filter,
)
from gshock_api.app_notification import AppNotification, NotificationType
from gshock_api.connection import Connection
from gshock_api.event import Event, RepeatPeriod, create_event_date
from gshock_api.exceptions import GShockConnectionError
from gshock_api.gshock_api import GshockAPI
from gshock_api.iolib.health_data_io import HealthDataIO, DailyHealthData
from gshock_api.logger import logger
from gshock_api.watch_info import watch_info

async def main(argv: Sequence[str]) -> None:
    await run_api_tests(argv)

def prompt() -> None:
    logger.info(
        "========================================================================"
    )
    logger.info(
        "Press and hold lower-left button on your watch for 3 seconds to start..."
    )
    logger.info(
        "========================================================================"
    )
    logger.info("")


async def run_api_tests(argv: Sequence[str]) -> None:  # noqa: PLR0915
    prompt()

    try:
        logger.info("Waiting for connection...")
        connection = Connection()
        await connection.connect(watch_filter.connection_filter)
        logger.info("Connected...")

        # Initialize connection for HealthDataIO
        HealthDataIO.connection = connection

        api = GshockAPI(connection)
        
        app_info = await api.get_app_info() 
        logger.info(f"app info: {app_info}")

        pressed_button = await api.get_pressed_button()
        logger.info(f"pressed button: {pressed_button}")

        if watch_info.hasHealthData:
            await test_health_data(api)

        # Disable other tests to avoid noise and ATT errors
        return

        # Create a single event
        tz = pytz.timezone("America/Toronto")
        dt = datetime.now()
        utc_timestamp = dt.timestamp()
        event_date = create_event_date(utc_timestamp, tz)
        event_date_str = json.dumps(event_date.__dict__)
        event_json_str = (
            """{"title":"Test Event", "time":{"selected":\""""
            + str(False)
            + """\", "enabled":\""""
            + str(True)
            + """\", "repeat_period":\""""
            + str(RepeatPeriod.WEEKLY)
            + """\","days_of_week":\""""
            + "MONDAY"
            + """\", "start_date":"""
            + event_date_str
            + """, "end_date":"""
            + event_date_str
            + """}}"""
        )
        Event().create_event(json.loads(event_json_str))
        logger.info(f"Created event: {pformat(json.loads(event_json_str))}")

        reminders = await api.get_reminders()
        for reminder in reminders:
            logger.info (f"reminder: {pformat(reminder)}")

        reminders[3]["title"] = "Test Event"

        await api.set_reminders(reminders)

    except GShockConnectionError as e:
        logger.info(f"Connection problem: {e}")

    input("Hit any key to disconnect")

    await connection.disconnect()
    logger.info("--- END OF TESTS ---")


async def run_api_tests_notifications() -> None:
    prompt()

    connection = Connection()
    await connection.connect()

    api = GshockAPI(connection)

    await app_notifications(api)

    input("Hit any key to disconnect")

    await connection.disconnect()
    logger.info("--- END OF TESTS ---")


async def app_notifications(api: GshockAPI) -> None:
    AppNotification(
        type=NotificationType.CALENDAR,
        timestamp="20231001T121000",
        app="Calendar",
        title="This is a very long Meeting with Team",
        text=" 9:20 - 10:15 AM",
    )

    AppNotification(
        type=NotificationType.CALENDAR,
        timestamp="20250516T233000",
        app="Calendar",
        title="Full day event 3",
        text="Tomorrow",
    )

    email_notification2 = AppNotification(
        type=NotificationType.EMAIL_SMS,
        timestamp="20250516T211520",
        app="Gmail",
        title="me",
        text="""[translate:彼女はピア
彼女はピアノを弾いたり、絵を描くのが好きです。リア充です
彼女はピア
彼女はピアノを弾いたり、絵を描くのが好きです。リア充です
彼女はピア
彼女はピアノを弾いたり、絵を描くのが好きです。リア充です
]""",
        short_text="""[translate:彼女はピア
彼女はピアノを弾いたり、絵を描くのが好きです。リア充です
彼女はピア
彼女はピアノを弾いたり、絵を描くのが好きです。リア充です
彼女はピア
彼女はピアノを弾いたり、絵を描くのが好きです。リア充です
]""",
    )

    AppNotification(
        type=NotificationType.EMAIL_SMS,
        timestamp="20250516T211520",
        app="Gmail",
        title="me",
        text="[translate:الساعة\n]",
    )

    AppNotification(
        type=NotificationType.EMAIL,
        timestamp="20231001T120000",
        app="EmailApp",
        title="Ivo",
        short_text="""And this is a short message up to 40 chars""",
        text="This is the message up to 193 characters, combined up to 206 characters",
    )

    await api.send_app_notification(email_notification2)


async def test_health_data(api: GshockAPI) -> None:
    logger.info("Testing Health Data request (GET_HEALTH_DATA) via API...")
    
    all_data = []
    
    def on_health_update(data: DailyHealthData):
        logger.info(f"CALLBACK RECEIVED HEALTH DATA:\n{data}")
        # Dedup by date + snapshot count or just keep all for now
        all_data.append(data)

    try:
        # Set callback
        from gshock_api.iolib.health_data_io import HealthDataIO
        HealthDataIO.on_data_update = on_health_update
        
        # Set indices for HealthDataIO.get_data
        HealthDataIO.indices = ["64", "63", "62", "61", "60"]

        # Start request
        await api.get_health_data()
        
        # Give it a bit more time to collect the other indices
        await asyncio.sleep(15.0)
        
    except Exception as e:
        logger.error(f"Health data request failed: {e}")
    
    # Final sorted print
    if all_data:
        # Sort by date
        all_data.sort(key=lambda d: d.date)
        
        logger.info("\n" + "="*40)
        logger.info("FINAL COLLECTED HEALTH HISTORY:")
        logger.info("="*40)
        
        for daily in all_data:
            logger.info(daily)
            logger.info("-" * 20)
        logger.info("="*40)
    else:
        logger.info("Final collection contains 0 records.")
    logger.info("\n")

def convert_time_string_to_epoch(time_string: str) -> float | None:
    try:
        time_object = datetime.strptime(time_string, "%H:%M:%S")
        return time_object.timestamp()
    except ValueError:
        logger.info("Invalid time format. Please use the format HH:MM:SS.")
        return None


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
