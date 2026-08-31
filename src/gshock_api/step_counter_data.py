from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class StepCounterData:
    """ABL-100WE life-log record representation."""

    timestamp: datetime = None
    hourly_steps: list[int | None] = field(default_factory=list)
    daily_history: list[int | None] = field(default_factory=list)
    current_day_steps: int | None = None

    @classmethod
    def unavailable(cls) -> "StepCounterData":
        return cls(None, [], [], None)
