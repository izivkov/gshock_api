import logging
from typing import Final, TypeVar, Any

from gshock_api.connection import Connection  # type: ignore
from gshock_api.iolib.app_notification_io import AppNotificationIO
from gshock_api.iolib.button_pressed_io import WatchButton
from gshock_api.iolib.dst_watch_state_io import DtsState
from gshock_api.model.step_counter_data import StepCounterData
from gshock_api.watch_info import watch_info

T = TypeVar("T")

HANDLE_NOTIFICATION: Final[int] = 0x0D


class GshockAPI:
    """Main interface for interacting with Casio G-Shock watches."""

    logger = logging.getLogger("GshockAPI")

    def __init__(self, connection: Connection) -> None:
        self.connection: Connection = connection

    async def get_watch_name(self) -> str:
        """Get the name of the watch."""
        return await watch_info.protocol.get_watch_name(self.connection)

    async def get_pressed_button(self) -> WatchButton:
        """Tells which button was pressed on the watch to initiate the connection."""
        return await watch_info.protocol.get_pressed_button(self.connection)

    async def get_world_cities(self, city_number: int) -> str:
        """Get the name for a particular World City set on the watch."""
        return await watch_info.protocol.get_world_cities(self.connection, city_number)

    async def get_dst_for_world_cities(self, city_number: int) -> str:
        """Get the Daylight Saving Time for a particular World City set on the watch."""
        return await watch_info.protocol.get_dst_for_world_cities(self.connection, city_number)

    async def get_dst_watch_state(self, state: DtsState) -> str:
        """Get the DST state of the watch."""
        return await watch_info.protocol.get_dst_watch_state(self.connection, state)

    async def get_home_time(self, slot: int = 0) -> str:
        """Get HomeTime for the watch via current watch protocol."""
        return await watch_info.protocol.get_home_time(self.connection)

    async def set_time(
        self, current_time: object | None = None, offset: int = 0
    ) -> None:
        """Sets current time on the watch via current WatchProtocol."""
        await watch_info.protocol.set_time(self.connection, current_time, offset)

    async def get_alarms(self) -> list[Any]:
        """Gets alarms from the watch via current WatchProtocol."""
        return await watch_info.protocol.get_alarms(self.connection)

    async def set_alarms(self, alarms: list[Any]) -> None:
        """Sets alarms on the watch via current WatchProtocol."""
        await watch_info.protocol.set_alarms(self.connection, alarms)

    async def get_timer(self) -> int:
        """Get Timer value in seconds via current WatchProtocol."""
        return await watch_info.protocol.get_timer(self.connection)

    async def set_timer(self, timer_value: int) -> None:
        """Set Timer value in seconds via current WatchProtocol."""
        await watch_info.protocol.set_timer(self.connection, timer_value)

    async def get_watch_condition(self) -> Any:
        """Gets watch condition from the watch."""
        return await watch_info.protocol.get_watch_condition(self.connection)

    async def get_time_adjustment(self) -> Any:
        """Determine if auto-time adjustment is set or not."""
        return await watch_info.protocol.get_time_adjustment(self.connection)

    async def set_time_adjustment(
        self, time_adjustment: bool, minutes_after_hour: int
    ) -> None:
        """Sets auto-time adjustment for the watch."""
        await watch_info.protocol.set_time_adjustment(self.connection, time_adjustment, minutes_after_hour)

    async def get_basic_settings(self) -> dict:
        """Get basic settings from watch via current WatchProtocol."""
        return await watch_info.protocol.get_basic_settings(self.connection)

    async def get_settings(self) -> dict:
        """Gets settings from the watch via current WatchProtocol."""
        return await watch_info.protocol.get_settings(self.connection)

    async def set_settings(self, settings: Any) -> None:
        """Set settings to the watch via current WatchProtocol."""
        await watch_info.protocol.set_settings(self.connection, settings)

    async def get_step_count_today(self) -> int:
        """Gets the daily step count total for step counter supported watches."""
        return await watch_info.protocol.get_step_count_today(self.connection)

    async def get_step_summary(self) -> int:
        """Alias for a quick summary call that returns today's total steps.

        This is a lightweight call intended to return the current-day total
        without forcing the watch to finish a full history transfer.
        """
        return await watch_info.protocol.get_step_count_today(self.connection)

    async def get_step_count(self, peek: bool = False) -> StepCounterData:
        """Gets complete step counter data (hourly and daily history).

        The default behavior closes the transaction after the read so the connection
        remains usable for follow-up BLE commands such as time changes.
        """
        return await watch_info.protocol.get_step_count(self.connection, peek)

    async def get_step_history(self) -> StepCounterData:
        """Request the full step-history from the watch.

        This forces the watch to complete the transaction and return the
        complete hourly/daily history. Use when you need the full lifelog.
        """
        return await watch_info.protocol.get_step_count(self.connection, False)

    async def get_reminders(self) -> list[Any]:
        """Gets the current events (reminders) from the watch."""
        return [await self.get_event_from_watch(i) for i in range(1, 6)]

    async def get_event_from_watch(self, event_number: int) -> Any:
        """Gets a single event (reminder) from the watch."""
        return await watch_info.protocol.get_event_from_watch(self.connection, event_number)

    async def set_reminders(self, events: list[Any]) -> None:
        """Sets events (reminders) to the watch."""
        await watch_info.protocol.set_reminders(self.connection, events)

    async def get_app_info(self) -> str:
        """Gets app info from the watch."""
        return await watch_info.protocol.get_app_info(self.connection)

    async def send_app_notification(self, notification: dict[str, Any]) -> None:
        """Sends a notification to the watch display."""
        encoded_buffer: bytes = AppNotificationIO.encode_notification_packet(notification)
        encrypted_buffer: bytes = AppNotificationIO.xor_encode_buffer(encoded_buffer)
        await self.connection.write(HANDLE_NOTIFICATION, encrypted_buffer)
