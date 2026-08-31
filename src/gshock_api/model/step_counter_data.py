from dataclasses import dataclass, field


@dataclass
class StepCounterData:
    """ABL-100WE life-log record representation."""

    day_of_week: int = 0
    month: int = 0
    day_of_month: int = 0
    hourly_steps: list[int | None] = field(default_factory=list)
    daily_history: list[int | None] = field(default_factory=list)
    current_day_steps: int | None = None

    @classmethod
    def unavailable(cls) -> "StepCounterData":
        return cls(0, 0, 0, [], [], None)
