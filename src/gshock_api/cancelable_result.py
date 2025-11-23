import asyncio
from typing import TypeVar

from gshock_api.exceptions import GShockConnectionError

T = TypeVar("T")


class CancelableResult:
    """
    A mechanism to wait for an asynchronous result with a specified timeout,
    and safely set the result once it's available.
    """

    def __init__(self, timeout: float = 10.0) -> None:
        self._timeout: float = timeout
        self._future: asyncio.Future[T] = asyncio.Future()

    async def get_result(self) -> T:
        try:
            result: T = await asyncio.wait_for(
                self._future, timeout=self._timeout
            )
            return result
        except TimeoutError as e:
            if not self._future.done():
                # Setting None indicates no meaningful result
                self._future.set_result(None)  # type: ignore
            raise GShockConnectionError(
                f"Timeout occurred waiting for response from the watch: {e}"
            ) from e

    def set_result(self, result: T) -> None:
        if not self._future.done():
            self._future.set_result(result)


cancelable_result = CancelableResult()
