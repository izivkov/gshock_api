import asyncio
from typing import TypeVar

from gshock_api.exceptions import GShockConnectionError

# Define a TypeVar for flexibility, allowing the result to be any type
T = TypeVar('T')

class CancelableResult:
    """
    A mechanism to wait for an asynchronous result with a specified timeout,
    and safely set the result once it's available.
    """

    # Use T as the result type for the Future
    def __init__(self, timeout: float = 10.0) -> None:
        # Instance attributes with Type Hints
        self._timeout: float = timeout
        # Initialize an asyncio.Future that will eventually hold a value of type T (Any in this context)
        self._future: asyncio.Future[T] = asyncio.Future()

    # The method is an async coroutine that returns a value of type T (Any)
    async def get_result(self) -> T:
        try:
            # wait_for returns the result of the future if it completes within the timeout
            result: T = await asyncio.wait_for(
                self._future, 
                timeout=self._timeout
            )
            return result
        except TimeoutError as e:  # Catch asyncio.TimeoutError
            # Check if the future is still pending
            if not self._future.done():
                # Set a default result (e.g., empty string) or explicitly raise the exception.
                # Setting an empty string here ensures the future is done before raising.
                self._future.set_result(None) # Setting None or a default value might be cleaner

            # Raise the domain-specific exception, linking it to the original TimeoutError
            raise GShockConnectionError(f"Timeout occurred waiting for response from the watch: {e}") from e

    # Method takes a result of type T (Any) and returns nothing (None)
    def set_result(self, result: T) -> None:
        if not self._future.done():
            self._future.set_result(result)


# The instance can also be typed
cancelable_result: CancelableResult = CancelableResult()