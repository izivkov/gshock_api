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
    async def get_watch_name(self, connection: Any) -> str:
        """Gets the watch name."""
        pass

    @abstractmethod
    async def get_pressed_button(self, connection: Any) -> Any:
        """Gets the pressed button."""
        pass

    @abstractmethod
    async def get_world_cities(self, connection: Any, city_number: int) -> str:
        """Gets world cities."""
        pass

    @abstractmethod
    async def get_dst_for_world_cities(self, connection: Any, city_number: int) -> str:
        """Gets DST for world cities."""
        pass

    @abstractmethod
    async def get_dst_watch_state(self, connection: Any, state: Any) -> str:
        """Gets DST watch state."""
        pass

    @abstractmethod
    async def set_time(self, connection: Any, current_time: Any = None, offset: int = 0) -> None:
        """Sets the current time on the watch."""
        pass

    @abstractmethod
    async def get_timer(self, connection: Any) -> int:
        """Gets timer value from the watch."""
        pass

    @abstractmethod
    async def set_timer(self, connection: Any, timer_value: int) -> None:
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
    async def get_home_time(self, connection: Any) -> str:
        """Gets home time city from the watch."""
        pass

    @abstractmethod
    async def get_battery_level(self, connection: Any) -> int:
        """Gets battery level from watch condition."""
        pass

    @abstractmethod
    async def get_watch_temperature(self, connection: Any) -> int:
        """Gets watch temperature from watch condition."""
        pass

    @abstractmethod
    async def get_alarms(self, connection: Any) -> list[Any]:
        """Gets alarms from the watch."""
        pass

    @abstractmethod
    async def set_alarms(self, connection: Any, alarms: list[Any]) -> None:
        """Sets alarms on the watch."""
        pass

    @abstractmethod
    async def get_settings(self, connection: Any) -> dict[str, Any]:
        """Gets settings from the watch."""
        pass

    @abstractmethod
    async def set_settings(self, connection: Any, settings: Any) -> None:
        """Sets settings on the watch."""
        pass

    @abstractmethod
    async def get_basic_settings(self, connection: Any) -> dict[str, Any]:
        """Gets basic settings from the watch."""
        pass

    @abstractmethod
    async def get_time_adjustment(self, connection: Any) -> Any:
        """Gets time adjustment setting from the watch."""
        pass

    @abstractmethod
    async def set_time_adjustment(
        self, connection: Any, time_adjustment: bool, minutes_after_hour: int
    ) -> None:
        """Sets time adjustment setting on the watch."""
        pass

    @abstractmethod
    async def get_watch_condition(self, connection: Any) -> Any:
        """Gets watch condition from the watch."""
        pass

    @abstractmethod
    async def get_app_info(self, connection: Any) -> str:
        """Gets app info from the watch."""
        pass

    @abstractmethod
    async def get_step_count_today(self, connection: Any) -> int:
        """Gets daily step count total from the watch."""
        pass

    @abstractmethod
    async def get_step_count(self, connection: Any, reset: bool) -> Any:
        """Gets complete step counter data from the watch."""
        pass

    @abstractmethod
    async def get_event_from_watch(self, connection: Any, event_number: int) -> Any:
        """Gets an event from the watch."""
        pass

    @abstractmethod
    async def set_reminders(self, connection: Any, events: list[Any]) -> None:
        """Sets reminders on the watch."""
        pass
