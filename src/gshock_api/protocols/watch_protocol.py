from abc import ABC, abstractmethod
from typing import Any, Callable


class WatchProtocol(ABC):
    """Abstract base class defining the WatchProtocol interface for G-Shock watches."""

    @property
    @abstractmethod
    def data_received_handlers(self) -> dict[int, Callable[[bytes], None]]:
        """Maps characteristic key integers to handler functions."""
        pass

    @abstractmethod
    def extract_key(self, data: bytes) -> int | None:
        """Extracts characteristic key from received raw data bytes."""
        pass

    @abstractmethod
    def unwrap_payload(self, data: bytes, key: int) -> bytes:
        """Unwraps payload from envelope if necessary."""
        pass

    @abstractmethod
    def get_watch_condition_request(self) -> str:
        """Returns hex request command string for watch condition."""
        pass

    @abstractmethod
    async def set_time(self, api_inst: Any, current_time: Any = None, offset: int = 0) -> None:
        """Sets the current time on the watch."""
        pass

    @abstractmethod
    async def get_timer(self, api_inst: Any) -> int:
        """Gets timer value from the watch."""
        pass

    @abstractmethod
    async def set_timer(self, api_inst: Any, timer_value: int) -> None:
        """Sets timer value on the watch."""
        pass

    @abstractmethod
    def get_timer_request(self) -> str:
        """Returns timer request string."""
        pass

    @abstractmethod
    def get_timer_size(self) -> int:
        """Returns timer response size."""
        pass

    @abstractmethod
    async def get_home_time(self, api_inst: Any) -> str:
        """Gets home time city from the watch."""
        pass

    @abstractmethod
    async def get_battery_level(self, api_inst: Any) -> int:
        """Gets battery level from watch condition."""
        pass

    @abstractmethod
    async def get_watch_temperature(self, api_inst: Any) -> int:
        """Gets watch temperature from watch condition."""
        pass

    @abstractmethod
    async def get_alarms(self, api_inst: Any) -> list[Any]:
        """Gets alarms from the watch."""
        pass

    @abstractmethod
    async def set_alarms(self, api_inst: Any, alarms: list[Any]) -> None:
        """Sets alarms on the watch."""
        pass

    @abstractmethod
    async def get_settings(self, api_inst: Any) -> dict[str, Any]:
        """Gets settings from the watch."""
        pass

    @abstractmethod
    async def set_settings(self, api_inst: Any, settings: Any) -> None:
        """Sets settings on the watch."""
        pass

    @abstractmethod
    async def get_basic_settings(self, api_inst: Any) -> dict[str, Any]:
        """Gets basic settings from the watch."""
        pass

    @abstractmethod
    async def get_time_adjustment(self, api_inst: Any) -> bool:
        """Gets time adjustment setting from the watch."""
        pass
