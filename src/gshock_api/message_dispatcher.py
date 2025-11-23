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
from gshock_api.iolib.settings_io import SettingsIO
from gshock_api.iolib.time_adjustement_io import TimeAdjustmentIO
from gshock_api.iolib.time_io import TimeIO
from gshock_api.iolib.timer_io import TimerIO
from gshock_api.iolib.unknown_io import UnknownIO
from gshock_api.iolib.watch_condition_io import WatchConditionIO
from gshock_api.iolib.watch_name_io import WatchNameIO
from gshock_api.iolib.world_cities_io import WorldCitiesIO
from gshock_api.logger import logger

CHARACTERISTICS: Final[Mapping[str, int]] = CasioConstants.CHARACTERISTICS

# --- Type Aliases for Clarity ---

# Callable for sending messages (takes a JSON string or object, returns a coroutine that returns None)
# Since the message is a JSON string in send_to_watch, we use str.
SendToWatchFunction = Callable[[str], Coroutine[object, object, None]]

# Callable for handling received data (takes data, returns None)
# Data is indexed at [0] which suggests bytes or a list/tuple of bytes/ints.
# Assuming 'data' is a bytes/bytearray object.
OnReceivedFunction = Callable[[bytes], None]

class MessageDispatcher:
    """Dispatches high-level action messages to specific I/O handlers and routes 
    received characteristic data to the correct handler."""
    
    # Map of action strings (e.g., "SET_ALARMS") to their asynchronous handler functions.
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
    }

    # Map of Characteristic keys (integers from CHARACTERISTICS) to their synchronous handler functions.
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

        # ECB-30
        CHARACTERISTICS["CMD_SET_TIMEMODE"]: UnknownIO.on_received,
        CHARACTERISTICS["FIND_PHONE"]: UnknownIO.on_received,
    }

    @staticmethod
    async def send_to_watch(message: str) -> None:
        """Parses a JSON string message and dispatches it to the appropriate sender function."""
        
        # The JSON message contains a high-level action (e.g., "SET_ALARMS")
        # The result of json.loads is a dict[str, object]
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
    def on_received(data: bytes) -> None:
        """Routes received characteristic data to the appropriate handler based on the first byte (key)."""
        
        # Assuming the first byte of data contains the characteristic key/handle
        if not data:
            logger.info("Received empty data.")
            return

        # Key is the first byte/int value of the received data
        key: int = data[0]

        if key not in MessageDispatcher.data_received_messages:
            # We explicitly check against the keys of the CHARACTERISTICS map that are used
            # to make the error message more informative if needed.
            logger.info(f"Unknown characteristic key received: {key}")
        else:
            MessageDispatcher.data_received_messages[key](data)

# Usage example (unchanged logic)
if __name__ == "__main__":
    # Simulated messages
    # NOTE: The original example had sample_message as a dict, but send_to_watch expects a string.
    sample_message: str = '{"action": "GET_SETTINGS"}'
    # NOTE: The original example had sample_data as a string, but on_received expects bytes.
    # Assuming '1' is the key/handle for a characteristic.
    sample_data: bytes = b"\x01\x02\x03\x04\x05"

    # Simulated message dispatching
    # Note: send_to_watch is an async function and requires an async context to run properly.
    # For a real run, this would be `await MessageDispatcher.send_to_watch(sample_message)`
    # but we keep it synchronous for type-checking context.
    
    # This line is just for illustration in the if __name__ == "__main__" block
    # MessageDispatcher.send_to_watch(sample_message)  # noqa: ERA001
    # MessageDispatcher.on_received(sample_data)  # noqa: ERA001
    pass