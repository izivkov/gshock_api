import logging
from typing import Final

# Define a type for the logging level constants (e.g., logging.INFO, logging.DEBUG)
LogLevel: Final[int] = int

_logger: logging.Logger = logging.getLogger(__name__)


class Logger:
    """
    A simple wrapper around the standard Python logging module for consistent configuration.
    """
    # The default log level constant
    DEFAULT_LOG_LEVEL: Final[LogLevel] = logging.INFO # type: ignore

    def __init__(self, log_level: LogLevel = DEFAULT_LOG_LEVEL) -> None: # type: ignore
        self.log_level: LogLevel = log_level # type: ignore
        
        logging.basicConfig(
            level=self.log_level,
            handlers=[logging.StreamHandler()],
            format="%(asctime)-15s %(name)-8s %(levelname)s: %(message)s",
        )

    # Logging methods accept a variable number of arguments of unknown type (object)
    def error(self, *args: object) -> None:
        # Note: Logging functions often format the arguments into a single string
        _logger.error(args)

    def info(self, *args: object) -> None:
        _logger.info(args)

    def debug(self, *args: object) -> None:
        _logger.debug(args)

    def warn(self, *args: object) -> None:
        _logger.warn(args)

    def warning(self, *args: object) -> None:
        # Note: Calls warn() internally, which is standard practice
        _logger.warning(args)

# Instantiate the logger using the typed class
logger: Logger = Logger()