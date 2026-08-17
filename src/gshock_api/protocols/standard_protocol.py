import json
from typing import Any, Callable

from gshock_api.protocols.watch_protocol import WatchProtocol


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

    async def set_time(self, api_inst: Any, current_time: Any = None, offset: int = 0) -> None:
        from gshock_api.iolib.second_dial_io import SecondDialIO
        from gshock_api.watch_info import watch_info

        await api_inst.initialize_for_setting_time()
        await api_inst._set_time(current_time, offset)

        if watch_info.hasSecondDial:
            await SecondDialIO.set_second_dial(api_inst.connection)

    async def get_timer(self, api_inst: Any) -> int:
        return await api_inst._get_timer()

    async def set_timer(self, api_inst: Any, timer_value: int) -> None:
        message: str = f'{{"action": "SET_TIMER", "value": {timer_value} }}'
        await api_inst.connection.send_message(message)

    def get_timer_request(self) -> str:
        return "18"

    def get_timer_size(self) -> int:
        return 7

    async def get_home_time(self, api_inst: Any) -> str:
        from gshock_api import message_dispatcher
        return await message_dispatcher.WorldCitiesIO.request(api_inst.connection, 0)

    async def get_battery_level(self, api_inst: Any) -> int:
        cond = await api_inst.get_watch_condition()
        if isinstance(cond, dict):
            return cond.get("batteryLevel", 0)
        return getattr(cond, "battery_level", getattr(cond, "batteryLevel", 0))

    async def get_watch_temperature(self, api_inst: Any) -> int:
        cond = await api_inst.get_watch_condition()
        if isinstance(cond, dict):
            return cond.get("temperature", 0)
        return getattr(cond, "temperature", 0)

    async def get_alarms(self, api_inst: Any) -> list[Any]:
        return await api_inst._get_alarms()

    async def set_alarms(self, api_inst: Any, alarms: list[Any]) -> None:
        if not alarms:
            return
        alarms_str: str = json.dumps(alarms)
        set_action_cmd: str = f'{{"action":"SET_ALARMS", "value":{alarms_str} }}'
        await api_inst.connection.send_message(set_action_cmd)

    async def get_settings(self, api_inst: Any) -> dict[str, Any]:
        from gshock_api import message_dispatcher
        settings = await self.get_basic_settings(api_inst)
        try:
            time_adj_res = await message_dispatcher.TimeAdjustmentIO.request(api_inst.connection)
            if isinstance(settings, dict) and isinstance(time_adj_res, dict):
                val = time_adj_res.get("timeAdjusment") or time_adj_res.get("timeAdjustment")
                settings["timeAdjustment"] = str(val).lower() in ("true", "1")
        except Exception:
            pass
        return settings

    async def set_settings(self, api_inst: Any, settings: Any) -> None:
        setting_json: str = json.dumps(settings)
        message: str = f'{{"action": "SET_SETTINGS", "value": {setting_json} }}'
        await api_inst.connection.send_message(message)

    async def get_basic_settings(self, api_inst: Any) -> dict[str, Any]:
        from gshock_api import message_dispatcher
        result_str = await message_dispatcher.SettingsIO.request(api_inst.connection)
        if isinstance(result_str, dict):
            return result_str
        return json.loads(result_str)

    async def get_time_adjustment(self, api_inst: Any) -> bool:
        from gshock_api import message_dispatcher
        result = await message_dispatcher.TimeAdjustmentIO.request(api_inst.connection)
        if isinstance(result, dict):
            val = result.get("timeAdjusment") or result.get("timeAdjustment")
            return str(val).lower() in ("true", "1")
        return bool(result)
