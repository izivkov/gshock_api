from typing import Any

from gshock_api.protocols.standard_protocol import StandardProtocol


class MipProtocol(StandardProtocol):
    """Protocol for MIP display watches such as the GW-BX5600."""

    async def set_time(self, api_inst: Any, current_time: Any = None, offset: int = 0) -> None:
        from gshock_api import message_dispatcher
        await message_dispatcher.GwBx5600TimeIO.request(api_inst.connection, current_time, offset)
