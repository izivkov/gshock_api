from dataclasses import dataclass
from typing import TypedDict

from gshock_api.casio_constants import CasioConstants

HOURLY_CHIME_MASK: int = 0b10000000
ENABLED_MASK: int = 0b01000000
ALARM_CONSTANT_VALUE: int = 0x40


CHARACTERISTICS: dict[str, int] = CasioConstants.CHARACTERISTICS


class AlarmDict(TypedDict):
    enabled: bool
    hasHourlyChime: bool
    hour: int
    minute: int


@dataclass(frozen=True)
class Alarm:
    hour: int
    minute: int
    enabled: bool
    has_hourly_chime: bool


class Alarms:
    def __init__(self) -> None:
        self.alarms: list[AlarmDict] = []

    def clear(self) -> None:
        self.alarms.clear()

    def add_alarms(self, alarms: list[AlarmDict]) -> None:
        self.alarms.extend(alarms)


alarms_inst = Alarms()