from collections.abc import Callable, Coroutine, Mapping
import json
import logging
from typing import Final, TypeVar

from gshock_api import message_dispatcher
from gshock_api.alarms import alarms_inst
from gshock_api.connection import Connection  # type: ignore
from gshock_api.iolib.app_notification_io import AppNotificationIO
from gshock_api.iolib.button_pressed_io import WatchButton
from gshock_api.iolib.dst_watch_state_io import DtsState
from gshock_api.iolib.step_counter_io import StepCounterIO
from gshock_api.step_counter_data import StepCounterData
from gshock_api.utils import (
    to_compact_string,
    to_hex_string,
)
from gshock_api.watch_info import WatchModel, watch_info

T = TypeVar("T")

HANDLE_ALL_FEATURES: Final[int] = 0x0E
HANDLE_NOTIFICATION: Final[int] = 0x0D


class GshockAPI:
    """Main interface for interacting with Casio G-Shock watches."""

    logger = logging.getLogger("GshockAPI")

    def __init__(self, connection: Connection) -> None:
        self.connection: Connection = connection

    async def get_watch_name(self) -> str:
        """Get the name of the watch."""
        return await self._get_watch_name()

    async def _get_watch_name(self) -> str:
        result: str = await message_dispatcher.WatchNameIO.request(self.connection)
        return result

    async def get_pressed_button(self) -> WatchButton:
        """Tells which button was pressed on the watch to initiate the connection."""
        result: WatchButton = await message_dispatcher.ButtonPressedIO.request(self.connection)
        return result

    async def get_world_cities(self, city_number: int) -> str:
        """Get the name for a particular World City set on the watch."""
        return await self._get_world_cities(city_number)

    async def _get_world_cities(self, city_number: int) -> str:
        result: str = await message_dispatcher.WorldCitiesIO.request(self.connection, city_number)
        return result

    async def get_dst_for_world_cities(self, city_number: int) -> str:
        """Get the Daylight Saving Time for a particular World City set on the watch."""
        return await self._get_dst_for_world_cities(city_number)

    async def _get_dst_for_world_cities(self, city_number: int) -> str:
        result: str = await message_dispatcher.DstForWorldCitiesIO.request(
            self.connection, city_number
        )
        return result

    async def get_dst_watch_state(self, state: DtsState) -> str:
        """Get the DST state of the watch."""
        return await self._get_dst_watch_state(state)

    async def _get_dst_watch_state(self, state: DtsState) -> str:
        result: str = await message_dispatcher.DstWatchStateIO.request(
            self.connection, state
        )
        return result

    async def initialize_for_setting_time(self) -> None:
        await self.read_write_dst_watch_states()
        await self.read_write_dst_for_world_cities()

        if watch_info.hasWorldCities:
            print("Reading and writing world cities...")
            await self.read_write_world_cities()
        elif watch_info.model == WatchModel.MTG_B3000:
            print("Reading and writing home times...")
            await self.read_write_home_times()

    RequestFunction = Callable[[object], Coroutine[object, object, object]]

    async def get_home_time(self, slot: int = 0) -> str:
        """Get HomeTime for the watch via current watch protocol."""
        return await watch_info.protocol.get_home_time(self)

    async def read_write_home_times(self) -> None:
        for city_number in range(watch_info.worldCitiesCount):
            raw_bytes = await message_dispatcher.HomeTimeIO.request_raw(self.connection, city_number)
            hex_data: bytes = to_hex_string(raw_bytes)
            short_str: bytes = to_compact_string(hex_data)
            await self.connection.write(HANDLE_ALL_FEATURES, short_str)

    async def read_and_write(
        self, function: RequestFunction, param: object
    ) -> None:
        ret: object = await function(param)
        hex_data: bytes = to_hex_string(ret)
        short_str: bytes = to_compact_string(hex_data)
        await self.connection.write(HANDLE_ALL_FEATURES, short_str)

    async def read_write_dst_watch_states(self) -> None:
        array_of_dst_watch_state: list[dict[str, RequestFunction | DtsState]] = [
            {"function": self.get_dst_watch_state, "state": DtsState.ZERO},
            {"function": self.get_dst_watch_state, "state": DtsState.TWO},
            {"function": self.get_dst_watch_state, "state": DtsState.FOUR},
        ]
        for item in array_of_dst_watch_state[: watch_info.dstCount]:
            function: RequestFunction = item["function"]  # type: ignore[assignment]
            state: DtsState = item["state"]  # type: ignore[assignment]
            await self.read_and_write(function, state)

    async def read_write_dst_for_world_cities(self) -> None:
        fn = self.get_dst_for_world_cities
        for city_number in range(watch_info.worldCitiesCount):
            await self.read_and_write(fn, city_number)

    async def read_write_world_cities(self) -> None:
        fn = self.get_world_cities
        for city_number in range(watch_info.worldCitiesCount):
            await self.read_and_write(fn, city_number)

    async def set_time(
        self, current_time: object | None = None, offset: int = 0
    ) -> None:
        """Sets current time on the watch via current WatchProtocol."""
        await watch_info.protocol.set_time(self, current_time, offset)

    async def _set_time(self, current_time: object | None, offset: int = 0) -> None:
        await message_dispatcher.TimeIO.request(self.connection, current_time, offset)

    async def get_alarms(self) -> list[T]:
        """Gets alarms from the watch via current WatchProtocol."""
        return await watch_info.protocol.get_alarms(self)

    async def _get_alarms(self) -> list[T]:
        alarms_inst.clear()
        await message_dispatcher.AlarmsIO.request(self.connection)
        return alarms_inst.alarms

    async def set_alarms(self, alarms: list[T]) -> None:
        """Sets alarms on the watch via current WatchProtocol."""
        await watch_info.protocol.set_alarms(self, alarms)

    async def get_timer(self) -> int:
        """Get Timer value in seconds via current WatchProtocol."""
        return await watch_info.protocol.get_timer(self)

    async def _get_timer(self) -> int:
        result: int = await message_dispatcher.TimerIO.request(self.connection)
        return result

    async def set_timer(self, timer_value: int) -> None:
        """Set Timer value in seconds via current WatchProtocol."""
        await watch_info.protocol.set_timer(self, timer_value)

    async def get_watch_condition(self) -> object:
        """Gets watch condition from the watch."""
        req_cmd = watch_info.protocol.get_watch_condition_request()
        result: object = await message_dispatcher.WatchConditionIO.request(
            self.connection, request_cmd=req_cmd
        )
        return result

    async def get_time_adjustment(self) -> bool:
        """Determine if auto-time adjustment is set or not."""
        return await watch_info.protocol.get_time_adjustment(self)

    async def set_time_adjustment(
        self, time_adjustement: bool, minutes_after_hour: int
    ) -> None:
        """Sets auto-time adjustment for the watch."""
        message: str = f"""{{"action": "SET_TIME_ADJUSTMENT", "timeAdjustment": "{time_adjustement}", "minutesAfterHour": "{minutes_after_hour}" }}"""
        await self.connection.send_message(message)

    async def get_basic_settings(self) -> dict:
        """Get basic settings from watch via current WatchProtocol."""
        return await watch_info.protocol.get_basic_settings(self)

    async def get_settings(self) -> dict:
        """Gets settings from the watch via current WatchProtocol."""
        return await watch_info.protocol.get_settings(self)

    async def set_settings(self, settings: T) -> None:
        """Set settings to the watch via current WatchProtocol."""
        await watch_info.protocol.set_settings(self, settings)

    async def get_step_count(self) -> int:
        """Gets the daily step count total for step counter supported watches."""
        if not watch_info.hasStepCounter:
            self.logger.debug("Watch does not support step counter")
            return 0
        data = await StepCounterIO.request(self.connection)
        return data.current_day_steps if data.current_day_steps is not None else 0

    async def get_step_counter_data(self) -> StepCounterData:
        """Gets complete step counter data (hourly and daily history)."""
        if not watch_info.hasStepCounter:
            return StepCounterData.unavailable()
        return await StepCounterIO.request(self.connection)

    async def get_reminders(self) -> list[T]:
        return [await self.get_event_from_watch(i) for i in range(1, 6)]

    async def get_event_from_watch(self, event_number: int) -> T:
        result: T = await message_dispatcher.EventsIO.request(  # type: ignore[assignment]
            self.connection, event_number
        )
        return result

    async def set_reminders(self, events: list[T]) -> None:
        if not events:
            return

        def to_json(events_list: list[T]) -> list[Mapping[str, object]]:
            events_json: list[Mapping[str, object]] = []  # type: ignore[assignment]
            for event in events_list:
                events_json.append(event)  # type: ignore[arg-type]
            return events_json

        def get_enabled_events(events_list: list[Mapping[str, object]]) -> list[Mapping[str, object]]:
            return [event for event in events_list if event.get("time", {}).get("enabled")]  # type: ignore[misc]

        events_as_json: list[Mapping[str, object]] = to_json(events)
        enabled: list[Mapping[str, object]] = get_enabled_events(events_as_json)

        await self.connection.send_message(
            f"""{{"action": "SET_REMINDERS", "value": {json.dumps(enabled)}}}"""
        )

    async def get_app_info(self) -> str:
        result: str = await message_dispatcher.AppInfoIO.request(self.connection)
        return result

    async def send_app_notification(self, notification: dict[str, object]) -> None:
        encoded_buffer: bytes = AppNotificationIO.encode_notification_packet(notification)
        encrypted_buffer: bytes = AppNotificationIO.xor_encode_buffer(encoded_buffer)
        await self.connection.write(HANDLE_NOTIFICATION, encrypted_buffer)
