import json
from typing import Any, Callable
from gshock_api.iolib.dst_watch_state_io import DtsState
from gshock_api.utils import to_compact_string, to_hex_string

from gshock_api.protocols.watch_protocol import WatchProtocol

HANDLE_ALL_FEATURES = 0x0E

class StandardProtocol(WatchProtocol):
    """Standard protocol implementation for digital G-Shock watches."""

    @property
    def data_received_handlers(self) -> dict[int, Callable[[bytes], None]]:
        from gshock_api.message_dispatcher import MessageDispatcher
        return MessageDispatcher.data_received_messages

    def extract_key(self, data: bytes) -> int | None:
        if not data:
            return None
        return data[0]

    def unwrap_payload(self, data: bytes, key: int) -> bytes:
        return data

    def get_watch_condition_request(self) -> str:
        return "28"

    async def get_watch_name(self, connection: Any) -> str:
        from gshock_api import message_dispatcher
        return await message_dispatcher.WatchNameIO.request(connection)

    async def get_pressed_button(self, connection: Any) -> Any:
        from gshock_api import message_dispatcher
        return await message_dispatcher.ButtonPressedIO.request(connection)

    async def get_world_cities(self, connection: Any, city_number: int) -> str:
        from gshock_api import message_dispatcher
        return await message_dispatcher.WorldCitiesIO.request(connection, city_number)

    async def get_dst_for_world_cities(self, connection: Any, city_number: int) -> str:
        from gshock_api import message_dispatcher
        return await message_dispatcher.DstForWorldCitiesIO.request(connection, city_number)

    async def get_dst_watch_state(self, connection: Any, state: Any) -> str:
        from gshock_api import message_dispatcher
        return await message_dispatcher.DstWatchStateIO.request(connection, state)

    async def set_time(self, connection: Any, current_time: Any = None, offset: int = 0) -> None:
        from gshock_api.iolib.second_dial_io import SecondDialIO
        from gshock_api.watch_info import watch_info
        from gshock_api import message_dispatcher

        await self.initialize_for_setting_time(connection)
        await message_dispatcher.TimeIO.request(connection, current_time, offset)

        if watch_info.hasSecondDial:
            await SecondDialIO.set_second_dial(connection)

    async def initialize_for_setting_time(self, connection: Any) -> None:
        from gshock_api.watch_info import watch_info, WatchModel

        await self.read_write_dst_watch_states(connection)
        await self.read_write_dst_for_world_cities(connection)

        if watch_info.hasWorldCities:
            await self.read_write_world_cities(connection)
        elif watch_info.model == WatchModel.MTG_B3000:
            await self.read_write_home_times(connection)

    async def read_write_dst_watch_states(self, connection: Any) -> None:
        from gshock_api.watch_info import watch_info
        for state in [DtsState.ZERO, DtsState.TWO, DtsState.FOUR][:watch_info.dstCount]:
            await self.read_and_write(connection, self.get_dst_watch_state, state)

    async def read_write_dst_for_world_cities(self, connection: Any) -> None:
        from gshock_api.watch_info import watch_info
        for city_number in range(watch_info.worldCitiesCount):
            await self.read_and_write(connection, self.get_dst_for_world_cities, city_number)

    async def read_write_world_cities(self, connection: Any) -> None:
        from gshock_api.watch_info import watch_info
        for city_number in range(watch_info.worldCitiesCount):
            await self.read_and_write(connection, self.get_world_cities, city_number)

    async def read_write_home_times(self, connection: Any) -> None:
        from gshock_api.watch_info import watch_info
        from gshock_api import message_dispatcher
        for city_number in range(watch_info.worldCitiesCount):
            raw_bytes = await message_dispatcher.HomeTimeIO.request_raw(connection, city_number)
            hex_data = to_hex_string(raw_bytes)
            short_str = to_compact_string(hex_data)
            await connection.write(HANDLE_ALL_FEATURES, short_str)

    async def read_and_write(self, connection: Any, function: Callable, param: Any) -> None:
        ret = await function(connection, param)
        hex_data = to_hex_string(ret)
        short_str = to_compact_string(hex_data)
        await connection.write(HANDLE_ALL_FEATURES, short_str)

    async def get_timer(self, connection: Any) -> int:
        from gshock_api import message_dispatcher
        return await message_dispatcher.TimerIO.request(connection)

    async def set_timer(self, connection: Any, timer_value: int) -> None:
        message = f'{{"action": "SET_TIMER", "value": {timer_value} }}'
        await connection.send_message(message)

    def get_timer_request(self) -> str:
        return "18"

    def get_timer_size(self) -> int:
        return 7

    async def get_home_time(self, connection: Any) -> str:
        from gshock_api import message_dispatcher
        return await message_dispatcher.WorldCitiesIO.request(connection, 0)

    async def get_battery_level(self, connection: Any) -> int:
        cond = await self.get_watch_condition(connection)
        if isinstance(cond, dict):
            return cond.get("batteryLevel", 0)
        return getattr(cond, "battery_level", getattr(cond, "batteryLevel", 0))

    async def get_watch_temperature(self, connection: Any) -> int:
        cond = await self.get_watch_condition(connection)
        if isinstance(cond, dict):
            return cond.get("temperature", 0)
        return getattr(cond, "temperature", 0)

    async def get_alarms(self, connection: Any) -> list[Any]:
        from gshock_api.alarms import alarms_inst
        from gshock_api import message_dispatcher
        alarms_inst.clear()
        await message_dispatcher.AlarmsIO.request(connection)
        return alarms_inst.alarms

    async def set_alarms(self, connection: Any, alarms: list[Any]) -> None:
        if not alarms:
            return
        alarms_str = json.dumps(alarms)
        set_action_cmd = f'{{"action":"SET_ALARMS", "value":{alarms_str} }}'
        await connection.send_message(set_action_cmd)

    async def get_settings(self, connection: Any) -> dict[str, Any]:
        from gshock_api import message_dispatcher
        settings = await self.get_basic_settings(connection)
        try:
            time_adj_res = await message_dispatcher.TimeAdjustmentIO.request(connection)
            if isinstance(settings, dict) and isinstance(time_adj_res, dict):
                val = time_adj_res.get("timeAdjustment")
                settings["time_adjustment"] = str(val).lower() in ("true", "1")
        except Exception:
            pass
        return settings

    async def set_settings(self, connection: Any, settings: Any) -> None:
        setting_json = json.dumps(settings)
        message = f'{{"action": "SET_SETTINGS", "value": {setting_json} }}'
        await connection.send_message(message)

    async def get_basic_settings(self, connection: Any) -> dict[str, Any]:
        from gshock_api import message_dispatcher
        result_str = await message_dispatcher.SettingsIO.request(connection)
        if isinstance(result_str, dict):
            return result_str
        return json.loads(result_str)

    async def get_time_adjustment(self, connection: Any) -> Any:
        from gshock_api import message_dispatcher
        result = await message_dispatcher.TimeAdjustmentIO.request(connection)
        if isinstance(result, dict):
            val = result.get("timeAdjustment")
            return str(val).lower() in ("true", "1")
        return bool(result)

    async def set_time_adjustment(self, connection: Any, time_adjustment: bool, minutes_after_hour: int) -> None:
        message = f'{{"action": "SET_TIME_ADJUSTMENT", "timeAdjustment": "{time_adjustment}", "minutesAfterHour": "{minutes_after_hour}" }}'
        await connection.send_message(message)

    async def get_watch_condition(self, connection: Any) -> Any:
        from gshock_api import message_dispatcher
        req_cmd = self.get_watch_condition_request()
        return await message_dispatcher.WatchConditionIO.request(connection, request_cmd=req_cmd)

    async def get_app_info(self, connection: Any) -> str:
        from gshock_api import message_dispatcher
        return await message_dispatcher.AppInfoIO.request(connection)

    async def get_step_count_today(self, connection: Any) -> int:
        from gshock_api.iolib.step_counter_io import StepCounterIO
        data = await StepCounterIO.request(connection)
        return data.current_day_steps if data.current_day_steps is not None else 0

    async def get_step_count(self, connection: Any, peek: bool = True) -> Any:
        from gshock_api.iolib.step_counter_io import StepCounterIO
        return await StepCounterIO.request(connection, peek)

    async def get_event_from_watch(self, connection: Any, event_number: int) -> Any:
        from gshock_api import message_dispatcher
        return await message_dispatcher.EventsIO.request(connection, event_number)

    async def set_reminders(self, connection: Any, events: list[Any]) -> None:
        if not events:
            return

        enabled = [event for event in events if event.get("time", {}).get("enabled")]
        await connection.send_message(f'{{"action": "SET_REMINDERS", "value": {json.dumps(enabled)}}}')
