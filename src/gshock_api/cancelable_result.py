import asyncio
from typing import Generic, TypeVar

from gshock_api.exceptions import GShockConnectionError

T = TypeVar("T")


class CancelableResult(Generic[T]):  # noqa: UP046
    """
    A mechanism to wait for an asynchronous result with a specified timeout,
    and safely set the result once it's available.
    """

    def __init__(self, timeout: float = 10.0) -> None:
        self._timeout = timeout

        # Create the future using the current event loop
        loop = asyncio.get_running_loop()
        self._future: asyncio.Future[T] = loop.create_future()

    async def get_result(self) -> T:
        try:
            return await asyncio.wait_for(self._future, timeout=self._timeout)

        except TimeoutError as e:
            # Ensure the future is finalized so callers won't hang forever
            if not self._future.done():
                self._future.set_exception(
                    GShockConnectionError(
                        f"Timeout waiting for response from the watch: {e}"
                    )
                )
            raise GShockConnectionError(
                f"Timeout waiting for response from the watch: {e}"
            ) from e

    def set_result(self, value: T) -> None:
        if not self._future.done():
            self._future.set_result(value)