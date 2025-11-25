import logging
from typing import Final

LogLevel: Final[int] = int

_logger: logging.Logger = logging.getLogger(__name__)


class Logger:
    """
    A simple wrapper around the standard Python logging module for consistent configuration.
    """
    DEFAULT_LOG_LEVEL: Final[LogLevel] = logging.INFO

    def __init__(self, log_level: LogLevel = DEFAULT_LOG_LEVEL) -> None:
        self.log_level = log_level

        logging.basicConfig(
            level=self.log_level,
            handlers=[logging.StreamHandler()],
            format="%(asctime)-15s %(name)-15s %(levelname)s: %(message)s",
        )

    def _join(self, *args: object) -> str:
        """Join args like print() does."""
        return " ".join(str(a) for a in args)

    # Logging methods -----------

    def error(self, *args: object) -> None:
        _logger.error(self._join(*args))

    def info(self, *args: object) -> None:
        _logger.info(self._join(*args))

    def debug(self, *args: object) -> None:
        _logger.debug(self._join(*args))

    def warn(self, *args: object) -> None:
        _logger.warning(self._join(*args))

    def warning(self, *args: object) -> None:
        _logger.warning(self._join(*args))


logger: Logger = Logger()
