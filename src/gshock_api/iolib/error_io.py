from gshock_api.logger import logger


class ErrorIO:
    @staticmethod
    def on_received(message: bytes) -> None:
        logger.info(f"ErrorIO onReceived: {message}")
