from collections.abc import Callable, Coroutine, Mapping
import json
import typing
from typing import Final

from gshock_api.casio_constants import CasioConstants
from gshock_api.iolib.alarms_io import AlarmsIO
from gshock_api.iolib.app_info_io import AppInfoIO
from gshock_api.iolib.button_pressed_io import ButtonPressedIO
from gshock_api.iolib.dst_for_world_cities_io import DstForWorldCitiesIO
from gshock_api.iolib.dst_watch_state_io import DstWatchStateIO
from gshock_api.iolib.error_io import ErrorIO
from gshock_api.iolib.events_io import EventsIO
from gshock_api.iolib.gw_bx5600_time_io import GwBx5600TimeIO
from gshock_api.iolib.home_time_io import HomeTimeIO
from gshock_api.iolib.settings_io import SettingsIO
from gshock_api.iolib.step_counter_io import StepCounterIO
from gshock_api.iolib.time_adjustement_io import TimeAdjustmentIO
from gshock_api.iolib.time_io import TimeIO
from gshock_api.iolib.timer_io import TimerIO
from gshock_api.iolib.unknown_io import UnknownIO
from gshock_api.iolib.watch_condition_io import WatchConditionIO
from gshock_api.iolib.watch_name_io import WatchNameIO
from gshock_api.iolib.world_cities_io import WorldCitiesIO
from gshock_api.logger import logger

CHARACTERISTICS: Final[Mapping[str, int]] = CasioConstants.CHARACTERISTICS

SendToWatchFunction = Callable[[str], Coroutine[object, object, None]]
OnReceivedFunction = Callable[[bytes], None]


class MessageDispatcher:
    """Dispatches high-level action messages to specific I/O handlers and routes
    received characteristic data to the correct handler using WatchProtocol."""

    watch_senders: typing.ClassVar[dict[str, SendToWatchFunction]] = {
        "GET_ALARMS": AlarmsIO.send_to_watch,
        "SET_ALARMS": AlarmsIO.send_to_watch_set,
        "SET_REMINDERS": EventsIO.send_to_watch_set,
        "GET_SETTINGS": SettingsIO.send_to_watch,
        "SET_SETTINGS": SettingsIO.send_to_watch_set,
        "GET_TIME_ADJUSTMENT": TimeAdjustmentIO.send_to_watch,
        "SET_TIME_ADJUSTMENT": TimeAdjustmentIO.send_to_watch_set,
        "GET_TIMER": TimerIO.send_to_watch,
        "SET_TIMER": TimerIO.send_to_watch_set,
        "SET_TIME": TimeIO.send_to_watch_set,
        "GET_HOME_TIME": HomeTimeIO.send_to_watch,
    }

    data_received_messages: typing.ClassVar[dict[int, OnReceivedFunction]] = {
        CHARACTERISTICS["CASIO_SETTING_FOR_ALM"]: AlarmsIO.on_received,
        CHARACTERISTICS["CASIO_SETTING_FOR_ALM2"]: AlarmsIO.on_received,
        CHARACTERISTICS["CASIO_TIMER"]: TimerIO.on_received,
        CHARACTERISTICS["CASIO_WATCH_NAME"]: WatchNameIO.on_received,
        CHARACTERISTICS["CASIO_DST_SETTING"]: DstForWorldCitiesIO.on_received,
        CHARACTERISTICS["CASIO_REMINDER_TIME"]: EventsIO.on_received,
        CHARACTERISTICS["CASIO_REMINDER_TITLE"]: EventsIO.on_received_title,
        CHARACTERISTICS["CASIO_WORLD_CITIES"]: WorldCitiesIO.on_received,
        CHARACTERISTICS["CASIO_DST_WATCH_STATE"]: DstWatchStateIO.on_received,
        CHARACTERISTICS["CASIO_WATCH_CONDITION"]: WatchConditionIO.on_received,
        CHARACTERISTICS["CASIO_APP_INFORMATION"]: AppInfoIO.on_received,
        CHARACTERISTICS["CASIO_BLE_FEATURES"]: ButtonPressedIO.on_received,
        CHARACTERISTICS["CASIO_SETTING_FOR_BASIC"]: SettingsIO.on_received,
        CHARACTERISTICS["CASIO_SETTING_FOR_BLE"]: TimeAdjustmentIO.on_received,
        CHARACTERISTICS["ERROR"]: ErrorIO.on_received,
        CHARACTERISTICS["UNKNOWN"]: UnknownIO.on_received,
        CHARACTERISTICS["CMD_SET_TIMEMODE"]: UnknownIO.on_received,
        CHARACTERISTICS["FIND_PHONE"]: UnknownIO.on_received,
        CHARACTERISTICS["CASIO_ACTIVITY_RECORD"]: StepCounterIO.on_received,
        CHARACTERISTICS["GW_BX5600_SP_DATA_HEADER_03"]: GwBx5600TimeIO.on_received,
        CHARACTERISTICS["GW_BX5600_SP_DATA_HEADER_05"]: GwBx5600TimeIO.on_received,
        CHARACTERISTICS["GW_BX5600_SP_DATA_HEADER_06"]: GwBx5600TimeIO.on_received,
        CHARACTERISTICS["CASIO_HOME_TIME"]: HomeTimeIO.on_received,
    }

    @staticmethod
    async def send_to_watch(message: str) -> None:
        """Parses a JSON string message and dispatches it to the appropriate sender function."""
        try:
            json_message: dict[str, object] = json.loads(message)
        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON message: {message}")
            return

        action: object | None = json_message.get("action")
        if not isinstance(action, str):
            logger.error(f"Message has no valid 'action' key: {message}")
            return

        if action in MessageDispatcher.watch_senders:
            await MessageDispatcher.watch_senders[action](message)
        else:
            logger.error(f"Unknown action received: {action}")

    @staticmethod
    def on_received(data: bytes, protocol: typing.Any = None) -> None:
        """Routes received characteristic data to the appropriate handler based on protocol key extraction."""
        from gshock_api.watch_info import watch_info

        if not data:
            logger.info("Received empty data.")
            return

        prot = protocol if protocol is not None else watch_info.protocol
        key = prot.extract_key(data)
        if key is None:
            logger.info("Could not extract key from data.")
            return

        handlers = prot.data_received_handlers
        if key not in handlers:
            logger.info(f"Unknown characteristic key received: {key}")
        else:
            unwrapped_data = prot.unwrap_payload(data, key)
            handlers[key](unwrapped_data)
