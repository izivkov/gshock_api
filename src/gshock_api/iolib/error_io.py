from gshock_api.logger import logger
from gshock_api.pending_requests_registry import PendingRequestsRegistry


class ErrorIO:
    @staticmethod
    def on_received(message: str) -> None:
        logger.info(f"ErrorIO onReceived: {message}")
        # Cancel all pending requests to prevent blocking
        PendingRequestsRegistry.cancel_all(message)
