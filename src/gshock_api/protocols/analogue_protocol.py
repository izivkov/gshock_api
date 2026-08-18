from typing import Any

from gshock_api.protocols.standard_protocol import StandardProtocol


class AnalogueProtocol(StandardProtocol):
    """Protocol implementation for analogue G-Shock watches (e.g. MTG-B1000, MTG-B3000)."""

    def extract_key(self, data: bytes) -> int | None:
        if not data:
            return None

        first_byte = data[0]
        if first_byte == 0x28 and len(data) > 4:
            handlers = self.data_received_handlers
            if data[1] == 0x01 and data[4] in handlers:
                return data[4]
            elif data[1] == 0x00 and data[3] in handlers:
                return data[3]
            else:
                return 0x28
        return first_byte

    def unwrap_payload(self, data: bytes, key: int) -> bytes:
        if not data:
            return data

        if data[0] == 0x28 and key != 0x28:
            skip = 4 if (len(data) > 1 and data[1] == 0x01) else 3
            return data[skip:]
        return data

    def get_watch_condition_request(self) -> str:
        return "280000"

    async def set_time(self, connection: Any, current_time: Any = None, offset: int = 0) -> None:
        from gshock_api.iolib.second_dial_io import SecondDialIO
        from gshock_api.watch_info import watch_info
        from gshock_api import message_dispatcher

        await self.read_write_dst_watch_states(connection)
        await self.read_write_dst_for_world_cities(connection)
        await self.read_write_home_times(connection)
        await message_dispatcher.TimeIO.request(connection, current_time, offset)

        if watch_info.hasSecondDial:
            await SecondDialIO.set_second_dial(connection)

    def get_timer_request(self) -> str:
        return "182000"

    def get_timer_size(self) -> int:
        return 15

    async def get_home_time(self, connection: Any) -> str:
        from gshock_api import message_dispatcher
        raw_bytes = await message_dispatcher.HomeTimeIO.request_raw(connection, 0)
        return raw_bytes.hex() if isinstance(raw_bytes, bytes) else str(raw_bytes)
