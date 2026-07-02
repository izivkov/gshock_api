from typing import Protocol, Callable, Any


class ConnectionProtocol(Protocol):
    async def request(self, code: str) -> None:
        ...

    async def write(self, handle: int, data: bytes | str) -> None:
        ...

    async def start_notify(
        self,
        handle: int,
        callback: Callable[[Any, bytearray], None],
    ) -> None:
        ...
