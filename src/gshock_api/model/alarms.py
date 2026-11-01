from dataclasses import dataclass
from typing import NotRequired, TypedDict

from gshock_api.casio_constants import CasioConstants

HOURLY_CHIME_MASK: int = 0b10000000
ENABLED_MASK: int = 0b01000000
ALARM_CONSTANT_VALUE: int = 0x40

# Unverified: no HCI capture in test_data contains these bits set.
# Confirm by creating one-time and snooze alarms in the official app and
# capturing the 0x15/0x16 writes before relying on these values.
ONE_TIME_MASK: int = 0b00100000
SNOOZE_MASK: int = 0b00010000


CHARACTERISTICS: dict[str, int] = CasioConstants.CHARACTERISTICS


class AlarmDict(TypedDict):
    enabled: bool
    hasHourlyChime: bool
    hour: int
    minute: int
    oneTime: NotRequired[bool]
    snooze: NotRequired[bool]


@dataclass(frozen=True)
class Alarm:
    hour: int
    minute: int
    enabled: bool
    has_hourly_chime: bool
    one_time: bool = False
    snooze: bool = False


class Alarms:
    def __init__(self) -> None:
        self.alarms: list[AlarmDict] = []

    def clear(self) -> None:
        self.alarms.clear()

    def add_alarms(self, alarms: list[AlarmDict]) -> None:
        self.alarms.extend(alarms)


alarms_inst = Alarms()