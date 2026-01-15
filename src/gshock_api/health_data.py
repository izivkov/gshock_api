from dataclasses import dataclass
from datetime import datetime

@dataclass
class HealthData:
    timestamp: int  # Epoch timestamp
    steps: int
    calories: int
    distance: int = 0
    heart_rate_avg: int = 0
    heart_rate_max: int = 0
    heart_rate_min: int = 0

    def __repr__(self):
        dt = datetime.fromtimestamp(self.timestamp)
        return (f"HealthData(time={dt.strftime('%H:%M')}, steps={self.steps}, "
                f"calories={self.calories}, distance={self.distance}m)")

@dataclass
class DailyHealthData:
    date: str  # YYYY-MM-DD
    total_steps: int = 0
    total_calories: int = 0
    total_distance: int = 0
    snapshots: list[HealthData] = None

    def __post_init__(self):
        if self.snapshots is None:
            self.snapshots = []
        if self.snapshots:
            # Aggregate totals from snapshots (assuming they are cumulative or the last one is the day total)
            self.total_steps = max(s.steps for s in self.snapshots)
            self.total_calories = max(s.calories for s in self.snapshots)
            self.total_distance = max(s.distance for s in self.snapshots)

    def __repr__(self):
        snapshots_str = "\n    ".join([repr(s) for s in (self.snapshots or [])])
        return (
            f"DailyHealthData(date={self.date}):\n"
            f"  Total Steps:    {self.total_steps}\n"
            f"  Total Calories: {self.total_calories} kcal\n"
            f"  Total Distance: {self.total_distance} m\n"
            f"  Snapshots:\n    {snapshots_str}"
        )
