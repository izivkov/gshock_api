from gshock_api.logger import logger


class UnknownIO:
    @staticmethod
    def on_received(message: bytes) -> None:
        logger.info(f"UnknownIO onReceived: {message}")
