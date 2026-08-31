from __future__ import annotations  # Enables forward references like 'Event'

from dataclasses import dataclass
from datetime import datetime
import json
import types
from typing import TYPE_CHECKING, Final, TypeVar

if TYPE_CHECKING:
    from collections.abc import (  # Using Mapping for dict types where object values are complex
        Mapping,
    )
    from datetime import date, tzinfo

# Define a Type Variable T for generic message objects
T = TypeVar("T") 

@dataclass
class EventDate:
    year: int
    month: str
    day: int

    def to_json(self) -> dict[str, int | str]:
        """Converts the EventDate instance attributes to a dictionary."""
        # The values are simple types: int and str
        return self.__dict__
    
    def equals(self, event_date: EventDate) -> bool:
        """Compares this EventDate to another EventDate object."""
        return (
            event_date.year == self.year
            and event_date.month == self.month
            and event_date.day == self.day
        )

    def __str__(self) -> str:
        return f"year: {self.year}, month: {self.month}, day: {self.day}"


@dataclass
class RepeatPeriod:
    """Defines the available repeat periods as constants."""
    # Note: period_duration is not used or initialized here, so it is removed.

    # Class-level constants (Final to indicate they should not be changed)
    NEVER: Final[str] = "NEVER"
    DAILY: Final[str] = "DAILY"
    WEEKLY: Final[str] = "WEEKLY"
    MONTHLY: Final[str] = "MONTHLY"
    YEARLY: Final[str] = "YEARLY"


# Global Constants for Days and Months
DAY_OF_WEEK: Final[list[str]] = [
    "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY",
]

MONTH_NAMES: Final[list[str]] = [
    "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", 
    "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"
]


def create_event_date(time_ms: float, zone: tzinfo) -> EventDate:
    """Creates an EventDate object from a Unix timestamp and a timezone."""
    start: date = datetime.fromtimestamp(time_ms, zone).date()
    # start.month is an int, so we explicitly cast to str to match EventDate definition
    return EventDate(start.year, str(start.month), start.day)


@dataclass
class Event:
    title: str = ""
    start_date: EventDate | None = None
    end_date: EventDate | None = None
    repeat_period: str = RepeatPeriod.NEVER 
    days_of_week: list[str] | None = None
    enabled: bool = False
    incompatible: bool = False
    selected: bool = False

    def __str__(self) -> str:
        start_str: str = self.start_date.__str__() if self.start_date else "None"
        end_str: str = self.end_date.__str__() if self.end_date else "None"
        return f"""Title: {self.title}, 
        startDate: {start_str}, 
        endDate: {end_str}, 
        repeatPeriod: {self.repeat_period}, 
        daysOfWeek: {self.days_of_week}, 
        enabled: {self.enabled}, 
        incompatible: {self.incompatible}, 
        selected: {self.selected}"""

    # event_jsn is a complex JSON object; using Mapping[str, object] is the best non-Any type
    def create_event(self, event_jsn: Mapping[str, object]) -> Event:
        """Populates the Event instance from a JSON dictionary."""
        
        def get_array_list_from_json_array(json_array: list[str]) -> list[str]:
            """Converts a list of day strings to a list of day strings (identity mapping)."""
            list_result: list[str] = []

            def string_to_day_of_week(day_str: str) -> str:
                return day_str

            for day_str in json_array:
                day_of_week_str: str = string_to_day_of_week(day_str)
                list_result.append(day_of_week_str)

            return list_result

        def string_to_month(month_str: str) -> str:
            """Maps a lowercase month string to its uppercase constant name."""
            month_map: dict[str, str] = {
                m.lower(): m for m in MONTH_NAMES
            }
            return month_map.get(month_str.lower(), MONTH_NAMES[0]) # Use JANUARY as fallback

        def string_to_repeat_period(repeat_period_str: str) -> str:
            """Maps a repeat period string to its corresponding RepeatPeriod constant string."""
            repeat_str: str = repeat_period_str.lower()
            if repeat_str == "daily":
                return RepeatPeriod.DAILY
            if repeat_str == "weekly":
                return RepeatPeriod.WEEKLY
            if repeat_str == "monthly":
                return RepeatPeriod.MONTHLY
            if repeat_str == "yearly":
                return RepeatPeriod.YEARLY
            if repeat_str == "never":
                return RepeatPeriod.NEVER
            return RepeatPeriod.NEVER

        # time_obj is a complex dictionary, using Mapping[str, object]
        time_obj: Mapping[str, object] = event_jsn.get("time", {})
        
        self.title = event_jsn.get("title", self.title)
        
        # NOTE: Assignments are kept as in the original logic, assuming the JSON structure 
        # is compatible with the EventDate | None and list[str] | None fields.
        self.start_date = time_obj.get("start_date", self.start_date)
        self.end_date = time_obj.get("end_date", self.end_date)
        
        self.days_of_week = time_obj.get("days_of_week", self.days_of_week)

        # Use explicit boolean conversion
        self.enabled = bool(time_obj.get("enabled", self.enabled))
        self.incompatible = bool(time_obj.get("incompatible", self.incompatible))
        self.selected = bool(time_obj.get("selected", self.selected))
        
        self.repeat_period = string_to_repeat_period(time_obj.get("repeat_period", self.repeat_period))
        
        return self

    # Parameters made optional using str | None
    def to_json(
        self,
        title: str | None = None,
        start_date: EventDate | None = None,
        end_date: EventDate | None = None,
        repeat_period: str | None = None,
        days_of_week: list[str] | None = None,
        enabled: bool | None = None,
        incompatible: bool | None = None,
        selected: bool | None = None,
    ) -> dict[str, object]: # Returning a complex JSON structure
        """Creates a JSON dictionary representation of the event."""
        
        # Use current instance values as defaults
        current_title: str = title if title is not None else self.title
        current_start_date: EventDate | None = start_date if start_date is not None else self.start_date
        current_end_date: EventDate | None = end_date if end_date is not None else self.end_date
        current_repeat_period: str = repeat_period if repeat_period is not None else self.repeat_period
        current_days_of_week: list[str] | None = days_of_week if days_of_week is not None else self.days_of_week
        current_enabled: bool = enabled if enabled is not None else self.enabled
        current_incompatible: bool = incompatible if incompatible is not None else self.incompatible
        current_selected: bool = selected if selected is not None else self.selected

        time_obj = types.SimpleNamespace()
        time_obj.repeatPeriod = current_repeat_period
        time_obj.daysOfWeek = current_days_of_week
        time_obj.enabled = current_enabled
        time_obj.incompatible = current_incompatible
        time_obj.selected = current_selected

        # The result of json.loads(json.dumps(...)) is a complex dictionary, using dict[str, object]
        time_json: dict[str, object] = json.loads(json.dumps(time_obj.__dict__))

        if current_start_date is None:
             raise ValueError("Event must have a start date to be converted to JSON.")

        time_json["start_date"] = current_start_date.toJson()

        if current_end_date is None:
            current_end_date = current_start_date
            
        time_json["end_date"] = current_end_date.toJson()

        event_json: dict[str, object] = {}
        event_json["title"] = current_title
        event_json["time"] = time_json

        return event_json