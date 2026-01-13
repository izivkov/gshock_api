from dataclasses import dataclass

@dataclass
class HealthData:
    timestamp: int  # Epoch timestamp
    steps: int
    calories: int
    distance: int = 0
    heart_rate_avg: int = 0
    heart_rate_max: int = 0
    heart_rate_min: int = 0
    # Additional fields can be added as needed

@dataclass
class DailyHealthData:
    date: str  # YYYY-MM-DD
    snapshots: list[HealthData]
