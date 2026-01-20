"""
Registry for tracking pending requests and canceling them on errors.

This module provides a centralized way to track all pending CancelableResult
instances. When an error occurs, all pending requests can be canceled at once.
"""

from typing import Any
from gshock_api.cancelable_result import CancelableResult
from gshock_api.exceptions import GShockConnectionError
from gshock_api.logger import logger


class PendingRequestsRegistry:
    """
    Centralized registry for tracking pending requests.
    
    When an error occurs (e.g., ErrorIO.on_received is called), all pending
    requests can be canceled to prevent blocking.
    """
    
    # Dictionary mapping request names to their CancelableResult instances
    _pending_requests: dict[str, CancelableResult[Any]] = {}
    
    @classmethod
    def register(cls, name: str, result: CancelableResult[Any]) -> None:
        """
        Register a pending request.
        
        Args:
            name: Unique identifier for the request (e.g., "WatchNameIO", "SettingsIO")
            result: The CancelableResult instance waiting for a response
        """
        cls._pending_requests[name] = result
        logger.debug(f"Registered pending request: {name}")
    
    @classmethod
    def unregister(cls, name: str) -> None:
        """
        Unregister a completed request.
        
        Args:
            name: Unique identifier for the request
        """
        if name in cls._pending_requests:
            del cls._pending_requests[name]
            logger.debug(f"Unregistered pending request: {name}")
    
    @classmethod
    def cancel_all(cls, error_message: str) -> None:
        """
        Cancel all pending requests with an error.
        
        This should be called when an error occurs (e.g., from ErrorIO.on_received)
        to unblock all waiting calls.
        
        Args:
            error_message: The error message to set on all pending requests
        """
        if not cls._pending_requests:
            logger.debug("No pending requests to cancel")
            return
        
        logger.info(f"Canceling {len(cls._pending_requests)} pending request(s) due to error: {error_message}")
        
        # Create a copy of the keys to avoid modifying dict during iteration
        pending_names = list(cls._pending_requests.keys())
        
        for name in pending_names:
            result = cls._pending_requests[name]
            # Set an exception on the future to unblock the waiting call
            try:
                # result.set_exception(
                #     GShockConnectionError(f"Request canceled due to error: {error_message}")
                # )
                result.set_result("")
                logger.debug(f"Canceled pending request: {name}")
            except Exception as e:
                logger.error(f"Failed to cancel request {name}: {e}")
            finally:
                # Remove from registry
                cls.unregister(name)
    
    @classmethod
    def get_pending_count(cls) -> int:
        """Get the number of pending requests."""
        return len(cls._pending_requests)
    
    @classmethod
    def clear(cls) -> None:
        """Clear all pending requests without canceling them."""
        cls._pending_requests.clear()
