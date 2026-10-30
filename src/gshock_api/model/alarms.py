from dataclasses import dataclass
import json
from typing import NotRequired, TypedDict

from gshock_api.casio_constants import CasioConstants
from gshock_api.logger import logger
from gshock_api.utils import to_int_array

HOURLY_CHIME_MASK: int = 0b10000000
ENABLED_MASK: int = 0b01000000
ALARM_CONSTANT_VALUE: int = 0x40
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

    def add_alarms(self, alarm_json_str_arr: list[str]) -> None:
        for alarm_json_str in alarm_json_str_arr:
            alarm: AlarmDict = json.loads(alarm_json_str)
            self.alarms.append(alarm)

    def from_json_alarm_first_alarm(self, alarm: AlarmDict) -> bytearray:
        return self.create_first_alarm(alarm)

    def create_first_alarm(self, alarm: AlarmDict) -> bytearray:
        flag: int = 0
        if alarm.get("enabled"):
            flag |= ENABLED_MASK
            if alarm.get("oneTime"):
                flag |= ONE_TIME_MASK
            elif alarm.get("snooze"):
                flag |= SNOOZE_MASK
        if alarm.get("hasHourlyChime"):
            flag |= HOURLY_CHIME_MASK

        return bytearray(
            [
                CHARACTERISTICS["CASIO_SETTING_FOR_ALM"],
                flag,
                ALARM_CONSTANT_VALUE,
                alarm.get("hour"),
                alarm.get("minute"),
            ]
        )

    def from_json_alarm_secondary_alarms(self, alarms_json: list[AlarmDict]) -> bytearray:
        if len(alarms_json) < 2:
            return bytearray()
        # Encode the alarms passed in, not the state left by the last read (self.alarms).
        return self.create_secondary_alarm(alarms_json[1:])

    def create_secondary_alarm(self, alarms: list[AlarmDict]) -> bytearray:
        all_alarms: bytearray = bytearray([CHARACTERISTICS["CASIO_SETTING_FOR_ALM2"]])

        for alarm in alarms:
            flag: int = 0
            if alarm.get("enabled"):
                flag |= ENABLED_MASK
                if alarm.get("oneTime"):
                    flag |= ONE_TIME_MASK
                elif alarm.get("snooze"):
                    flag |= SNOOZE_MASK
            if alarm.get("hasHourlyChime"):
                flag |= HOURLY_CHIME_MASK

            all_alarms += bytearray(
                [flag, ALARM_CONSTANT_VALUE, alarm.get("hour"), alarm.get("minute")]
            )

        return all_alarms


alarms_inst = Alarms()


class AlarmDecoder:
    def to_json(self, command: str) -> dict[str, list[str]]:
        json_response: dict[str, list[str]] = {}
        int_array: list[int] = to_int_array(command)
        alarms: list[str] = []

        if int_array[0] == CHARACTERISTICS["CASIO_SETTING_FOR_ALM"]:
            int_array.pop(0)
            alarms.append(self.create_json_alarm(int_array))
            json_response["ALARMS"] = alarms
        elif int_array[0] == CHARACTERISTICS["CASIO_SETTING_FOR_ALM2"]:
            int_array.pop(0)

            quarter_len: int = len(int_array) // 4
            subarr1 = int_array[:quarter_len]
            subarr2 = int_array[quarter_len : 2 * quarter_len]
            subarr3 = int_array[2 * quarter_len : 3 * quarter_len]
            subarr4 = int_array[3 * quarter_len :]

            alarms.append(self.create_json_alarm(subarr1))
            alarms.append(self.create_json_alarm(subarr2))
            alarms.append(self.create_json_alarm(subarr3))
            alarms.append(self.create_json_alarm(subarr4))

            json_response["ALARMS"] = alarms
        else:
            logger.warning(f"Unhandled Command {command}")

        return json_response

    def create_json_alarm(self, int_array: list[int]) -> str:
        # Some models clear byte 1 on read-back; alarm fields are bytes 0, 2 and 3.
        alarm = Alarm(
            hour=int_array[2],
            minute=int_array[3],
            enabled=bool(int_array[0] & ENABLED_MASK),
            has_hourly_chime=bool(int_array[0] & HOURLY_CHIME_MASK),
            one_time=bool(int_array[0] & ONE_TIME_MASK),
            snooze=bool(int_array[0] & SNOOZE_MASK) and not int_array[0] & ONE_TIME_MASK,
        )
        return self.to_json_new_alarm(alarm)

    def to_json_new_alarm(self, alarm: Alarm) -> str:
        return json.dumps(
            {
                "enabled": alarm.enabled,
                "hasHourlyChime": alarm.has_hourly_chime,
                "oneTime": alarm.one_time,
                "snooze": alarm.snooze,
                "hour": alarm.hour,
                "minute": alarm.minute,
            }
        )


alarm_decoder = AlarmDecoder()
