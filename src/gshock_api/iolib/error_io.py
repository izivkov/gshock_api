from gshock_api.logger import logger


class ErrorIO:
    @staticmethod
    def on_received(message) -> None:
        logger.info(f"ErrorIO onReceived: {message}")
