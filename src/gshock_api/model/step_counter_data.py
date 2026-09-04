from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class StepCounterData:
    """ABL-100WE life-log record representation.

    The library keeps the lightweight fields required for the public API, while also
    preserving optional raw/derived values when a watch record is present. Callers do
    not need to parse the raw BLE payload themselves.
    """

    # Timestamp covering year/month/day/hour/minute/second when available.
    timestamp: Optional[datetime] = None
    day_of_week: int | None = None
    month: int | None = None
    day_of_month: int | None = None
    hourly_steps: list[int | None] = field(default_factory=list)
    daily_history: list[int | None] = field(default_factory=list)
    daily_distances: list[int | None] = field(default_factory=list)
    
    # Friendly, pre-computed representations filled by the IO layer
    hourly_intervals: list[dict] = field(default_factory=list)
    hourly_by_hour: list[int | None] = field(default_factory=list)
    daily_history_list: list[dict] = field(default_factory=list)
    current_day_steps: int | None = None
    raw: bytes | None = None
    warnings: list[str] = field(default_factory=list)
    distance_meters: int | None = None
    pending_distance_meters: int | None = None
    total_distance_meters: int | None = None
    bcd_total_steps: int | None = None
    # Raw five-bucket intensity values for each committed activity interval.
    hourly_intensities: list[tuple[int, int, int, int, int]] = field(default_factory=list)
    # Raw pending buckets and committed distance components from the life-log.
    pending_intensity: tuple[int, ...] = ()
    committed_distances: list[int] = field(default_factory=list)

    @classmethod
    def unavailable(cls) -> "StepCounterData":
        return cls(
            timestamp=None,
            hourly_steps=[],
            daily_history=[],
            current_day_steps=None,
            raw=b"",
            warnings=["step counter unavailable"],
            distance_meters=None,
            pending_distance_meters=None,
            total_distance_meters=None,
            bcd_total_steps=None,
        )

    # NOTE: Friendly representations (hourly_intervals, hourly_by_hour,
    # daily_history_list) are populated by the IO layer when parsing raw
    # payloads. This keeps `StepCounterData` a plain data container.
