from collections.abc import Callable, Coroutine, Mapping
import json
import logging
from typing import Final, TypeVar

from gshock_api import message_dispatcher
from gshock_api.alarms import alarms_inst

# Assuming the Connection class from before is available, we define the type here
from gshock_api.connection import Connection  # type: ignore
from gshock_api.iolib.app_notification_io import AppNotificationIO
from gshock_api.iolib.button_pressed_io import WatchButton
from gshock_api.iolib.dst_watch_state_io import DtsState
from gshock_api.utils import (
    to_compact_string,
    to_hex_string,
)
from gshock_api.watch_info import watch_info

# Type variable for unknown request/message objects (e.g., Alarm, Event)
T = TypeVar("T") 

# Define constants for write handles based on previous context (Connection class)
# 0xE is the CASIO_ALL_FEATURES_CHARACTERISTIC_UUID (used for writing response back)
HANDLE_ALL_FEATURES: Final[int] = 0x0E
# 0xD is the CASIO_NOTIFICATION_CHARACTERISTIC_UUID (used for sending notifications)
HANDLE_NOTIFICATION: Final[int] = 0x0D


class GshockAPI:
    """
    This class contains all the API functions. This should the the main interface to the
    library.
    """

    logger = logging.getLogger("GshockAPI")

    def __init__(self, connection: Connection) -> None:
        # Assuming connection is the Connection class we typed previously
        self.connection: Connection = connection

    async def get_watch_name(self) -> str:
        """Get the name of the watch."""
        return await self._get_watch_name()

    async def _get_watch_name(self) -> str:
        # Assuming WatchNameIO.request returns a string
        result: str = await message_dispatcher.WatchNameIO.request(self.connection)
        return result

    async def get_pressed_button(self) -> WatchButton:
        """This function tells us which button was pressed on the watch to initiate the connection."""
        # Assuming ButtonPressedIO.request returns a WatchButton enum/object
        result: WatchButton = await message_dispatcher.ButtonPressedIO.request(self.connection)
        return result

    async def get_world_cities(self, city_number: int) -> str:
        """Get the name for a particular World City set on the watch."""
        return await self._get_world_cities(city_number)

    async def _get_world_cities(self, city_number: int) -> str:
        # Assuming WorldCitiesIO.request returns a string
        result: str = await message_dispatcher.WorldCitiesIO.request(self.connection, city_number)
        return result

    async def get_dst_for_world_cities(self, city_number: int) -> str:
        """Get the **Daylight Saving Time** for a particular World City set on the watch."""
        return await self._get_dst_for_world_cities(city_number)

    async def _get_dst_for_world_cities(self, city_number: int) -> str:
        # Assuming DstForWorldCitiesIO.request returns a string
        result: str = await message_dispatcher.DstForWorldCitiesIO.request(
            self.connection, city_number
        )
        return result

    async def get_dst_watch_state(self, state: DtsState) -> str:
        """Get the DST state of the watch."""
        return await self._get_dst_watch_state(state)

    async def _get_dst_watch_state(self, state: DtsState) -> str:
        # Assuming DstWatchStateIO.request returns a string
        result: str = await message_dispatcher.DstWatchStateIO.request(
            self.connection, state
        )
        return result

    async def initialize_for_setting_time(self) -> None:
        await self.read_write_dst_watch_states()
        await self.read_write_dst_for_world_cities()

        if watch_info.hasWorldCities:
            await self.read_write_world_cities()
    
    # Define a Callable type for the function that will be read
    RequestFunction = Callable[[object], Coroutine[object, object, object]]

    # Replaced Any with object, and made function parameter specific
    async def read_and_write(
        self, function: RequestFunction, param: object
    ) -> None:
        # The return type of the function is unknown, hence object
        ret: object = await function(param)
        
        # Assuming ret is convertible to bytes/bytearray by to_hex_string
        hex_data: bytes = to_hex_string(ret)
        short_str: bytes = to_compact_string(hex_data)
        
        # Replaced 0xE with HANDLE_ALL_FEATURES
        await self.connection.write(HANDLE_ALL_FEATURES, short_str)

    async def read_write_dst_watch_states(self) -> None:
        # Use dict instead of generic Map/Any
        array_of_dst_watch_state: list[dict[str, RequestFunction | DtsState]] = [  # noqa: F821 # type: ignore
            {"function": self.get_dst_watch_state, "state": DtsState.ZERO},
            {"function": self.get_dst_watch_state, "state": DtsState.TWO},
            {"function": self.get_dst_watch_state, "state": DtsState.FOUR},
        ]
        
        # Type inference for item and its keys
        for item in array_of_dst_watch_state[: watch_info.dstCount]:
            function: RequestFunction = item["function"] # type: ignore[assignment] noqa: F821 # type: ignore  # noqa: F821
            state: DtsState = item["state"] # type: ignore[assignment]
            await self.read_and_write(function, state)

    async def read_write_dst_for_world_cities(self) -> None:
        fn = self.get_dst_for_world_cities

        for city_number in range(watch_info.worldCitiesCount):
            await self.read_and_write(fn, city_number)

    async def read_write_world_cities(self) -> None:
        fn = self.get_world_cities

        for city_number in range(watch_info.worldCitiesCount):
            await self.read_and_write(fn, city_number)

    # current_time is unknown type, using object | None
    async def set_time(
        self, current_time: object | None = None, offset: int = 0
    ) -> None:
        """Sets the current time on the watch from the time on the device."""
        await self.initialize_for_setting_time()
        await self._set_time(current_time, offset)
        # current_time = None is redundant as it's a local variable/parameter

    async def _set_time(self, current_time: object | None, offset: int = 0) -> None:
        await message_dispatcher.TimeIO.request(self.connection, current_time, offset)

    # Assuming Alarm is a specific class, using TypeVar T
    async def get_alarms(self) -> list[T]:
        """Gets the current alarms from the watch."""
        alarms_inst.clear()
        await self._get_alarms()
        # Assuming alarms_inst.alarms returns list[T]
        return alarms_inst.alarms

    # Assuming AlarmsIO.request returns a complex object (object)
    async def _get_alarms(self) -> object:
        return await message_dispatcher.AlarmsIO.request(self.connection)

    # alarms is a list of unknown alarm objects (TypeVar T)
    async def set_alarms(self, alarms: list[T]) -> None:
        """Sets alarms to the watch."""
        if not alarms:
            self.logger.debug("Alarm model not initialised! Cannot set alarm")
            return

        # Assuming T objects are JSON serializable
        alarms_str: str = json.dumps(alarms)
        set_action_cmd: str = f'{{"action":"SET_ALARMS", "value":{alarms_str} }}'
        # connection.send_message expects T, which must be convertible to a watch message
        await self.connection.send_message(set_action_cmd)

    async def get_timer(self) -> int:
        """Get Timer value in seconds."""
        return await self._get_timer()

    async def _get_timer(self) -> int:
        # Assuming TimerIO.request returns an integer
        result: int = await message_dispatcher.TimerIO.request(self.connection)
        return result

    async def set_timer(self, timer_value: int) -> None:
        """Set Timer value in seconds."""
        message: str = f'{{"action": "SET_TIMER", "value": {timer_value} }}'
        await self.connection.send_message(message)

    # Watch condition request returns an unknown object (object)
    async def get_watch_condition(self) -> object:
        result: object = await message_dispatcher.WatchConditionIO.request(self.connection)
        return result

    async def get_time_adjustment(self) -> bool:
        """Determine if auto-tame adjustment is set or not"""
        # Assuming TimeAdjustmentIO.request returns a boolean
        result: bool = await message_dispatcher.TimeAdjustmentIO.request(self.connection)
        return result

    async def set_time_adjustment(
        self, time_adjustement: bool, minutes_after_hour: int
    ) -> None:
        """Sets auto-tame adjustment for the watch"""
        message: str = f"""{{"action": "SET_TIME_ADJUSTMENT", "timeAdjustment": "{time_adjustement}", "minutesAfterHour": "{minutes_after_hour}" }}"""
        await self.connection.send_message(message)

    # SettingsIO returns a list of unknown Setting objects (list[T])
    async def get_basic_settings(self) -> list[T]:
        """Get settings from the watch."""
        result: list[T] = await message_dispatcher.SettingsIO.request(self.connection) # type: ignore[assignment]
        return result

    # settings is an unknown settings object (T)
    async def set_settings(self, settings: T) -> None:
        """Set settings to the watch."""
        setting_json: str = json.dumps(settings)
        message: str = f'{{"action": "SET_SETTINGS", "value": {setting_json} }}'
        await self.connection.send_message(message)

    # get_reminders returns a list of unknown Event objects (list[T])
    async def get_reminders(self) -> list[T]:
        return [await self.get_event_from_watch(i) for i in range(1, 6)]

    # get_event_from_watch returns an unknown Event object (T)
    async def get_event_from_watch(self, event_number: int) -> T:
        """Gets a single event (reminder) from the watch."""
        result: T = await message_dispatcher.EventsIO.request( # type: ignore[assignment]
            self.connection, event_number
        )
        return result

    # events is a list of unknown Event objects (list[T])
    async def set_reminders(self, events: list[T]) -> None:
        """Sets events (reminders) to the watch."""
        if not events:
            return

        # Assuming T objects are dicts or have a .toJson() method that returns a dict[str, object]
        # Since json.loads("[]") is used, the intent is likely to convert the list of T to a list of JSON-compatible dicts.
        def to_json(events_list: list[T]) -> list[Mapping[str, object]]:
            events_json: list[Mapping[str, object]] = [] # type: ignore[assignment]
            for event in events_list:
                # Assuming event is already a dictionary, or convertible to one.
                # If T is the dataclass Event, the list needs to be converted before this.
                events_json.append(event) # type: ignore[arg-type]  # noqa: PERF402
            return events_json

        # Assuming event is a dict[str, object] structure
        def get_enabled_events(events_list: list[Mapping[str, object]]) -> list[Mapping[str, object]]:
            return [event for event in events_list if event.get("time", {}).get("enabled")] # type: ignore[misc]

        # We first convert the list of T to a list of dicts (Mapping[str, object])
        events_as_json: list[Mapping[str, object]] = to_json(events)
        enabled: list[Mapping[str, object]] = get_enabled_events(events_as_json)

        await self.connection.send_message(
            f"""{{"action": "SET_REMINDERS", "value": {json.dumps(enabled)}}}"""
        )

    async def get_app_info(self) -> str:
        """Gets and internally sets app info to the watch."""
        result: str = await message_dispatcher.AppInfoIO.request(self.connection)
        return result

    async def send_app_notification(self, notification: dict[str, object]) -> None:
        # Assuming AppNotificationIO methods handle the conversion of the dict values
        encoded_buffer: bytes = AppNotificationIO.encode_notification_packet(notification)
        encrypted_buffer: bytes = AppNotificationIO.xor_encode_buffer(encoded_buffer)
        
        await self.connection.write(HANDLE_NOTIFICATION, encrypted_buffer)
