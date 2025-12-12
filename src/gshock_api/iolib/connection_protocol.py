from typing import Protocol


class ConnectionProtocol(Protocol):
    async def request(self, code: str) -> None:
        ...

    async def write(self, handle: int, data: bytes | str) -> None:
        ...
