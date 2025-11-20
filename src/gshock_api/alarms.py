from dataclasses import dataclass
import json

from gshock_api.casio_constants import CasioConstants
from gshock_api.logger import logger
from gshock_api.utils import to_int_array

HOURLY_CHIME_MASK = 0b10000000
ENABLED_MASK = 0b01000000
ALARM_CONSTANT_VALUE = 0x40

CHARACTERISTICS = CasioConstants.CHARACTERISTICS


@dataclass(frozen=True)
class Alarm:
    hour: int
    minute: int
    enabled: bool
    has_hourly_chime: bool


class Alarms:
    def __init__(self):
        self.alarms = []

    def clear(self) -> None:
        self.alarms.clear()

    def add_alarms(self, alarm_json_str_arr: list[str]) -> None:
        for alarm_json_str in alarm_json_str_arr:
            alarm = json.loads(alarm_json_str)
            self.alarms.append(alarm)

    def from_json_alarm_first_alarm(self, alarm: dict) -> bytearray:
        return self.create_first_alarm(alarm)

    def create_first_alarm(self, alarm: dict) -> bytearray:
        flag = 0
        if alarm.get("enabled"):
            flag |= ENABLED_MASK
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

    def from_json_alarm_secondary_alarms(self, alarms_json: list) -> bytearray:
        if len(alarms_json) < 2:
            return bytearray()
        alarms = self.alarms[1:]
        return self.create_secondary_alarm(alarms)

    def create_secondary_alarm(self, alarms: list) -> bytearray:
        all_alarms = bytearray([CHARACTERISTICS["CASIO_SETTING_FOR_ALM2"]])

        for alarm in alarms:
            flag = 0
            if alarm.get("enabled"):
                flag |= ENABLED_MASK
            if alarm.get("hasHourlyChime"):
                flag |= HOURLY_CHIME_MASK

            all_alarms += bytearray(
                [flag, ALARM_CONSTANT_VALUE, alarm.get("hour"), alarm.get("minute")]
            )

        return all_alarms


alarms_inst = Alarms()


class AlarmDecoder:
    def to_json(self, command: str) -> dict:
        json_response = {}
        int_array = to_int_array(command)
        alarms = []

        if int_array[0] == CHARACTERISTICS["CASIO_SETTING_FOR_ALM"]:
            int_array.pop(0)
            alarms.append(self.create_json_alarm(int_array))
            json_response["ALARMS"] = alarms
        elif int_array[0] == CHARACTERISTICS["CASIO_SETTING_FOR_ALM2"]:
            int_array.pop(0)

            # replacement to above 2 lines
            alarms = []
            # split int_array into 4 subarrays
            quarter_len = len(int_array) // 4
            subarr1 = int_array[:quarter_len]
            subarr2 = int_array[quarter_len: 2 * quarter_len]
            subarr3 = int_array[2 * quarter_len: 3 * quarter_len]
            subarr4 = int_array[3 * quarter_len:]

            # create json alarms for each subarray
            alarms.append(self.create_json_alarm(subarr1))
            alarms.append(self.create_json_alarm(subarr2))
            alarms.append(self.create_json_alarm(subarr3))
            alarms.append(self.create_json_alarm(subarr4))
            # end replacement

            json_response["ALARMS"] = alarms
        else:
            logger.warning(f"Unhandled Command {command}")

        return json_response

    def create_json_alarm(self, int_array: list[int]) -> str:
        alarm = Alarm(
            hour=int_array[2],
            minute=int_array[3],
            enabled=bool(int_array[0] & ENABLED_MASK),
            has_hourly_chime=bool(int_array[0] & HOURLY_CHIME_MASK),
        )
        return self.to_json_new_alarm(alarm)

    def to_json_new_alarm(self, alarm: Alarm) -> str:
        return json.dumps(
            {
                "enabled": alarm.enabled,
                "hasHourlyChime": alarm.has_hourly_chime,
                "hour": alarm.hour,
                "minute": alarm.minute,
            }
        )


alarm_decoder = AlarmDecoder()
