import json
from dataclasses import dataclass
from typing import TypedDict

from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.logger import logger
from gshock_api.utils import (
    clean_str,
    dec_to_hex,
    to_ascii_string,
    to_byte_array,
    to_compact_string,
    to_hex_string,
    to_int_array,
)

CHARACTERISTICS: dict[str, int] = CasioConstants.CHARACTERISTICS


class ReminderMasks:
    YEARLY_MASK =    0b00001000
    MONTHLY_MASK =   0b00010000
    WEEKLY_MASK =    0b00000100

    SUNDAY_MASK =    0b00000001
    MONDAY_MASK =    0b00000010
    TUESDAY_MASK =   0b00000100
    WEDNESDAY_MASK = 0b00001000
    THURSDAY_MASK =  0b00010000
    FRIDAY_MASK =    0b00100000
    SATURDAY_MASK =  0b01000000

    ENABLED_MASK =   0b00000001


class DateDict(TypedDict):
    year: int
    month: str
    day: int


class ReminderTimeDict(TypedDict):
    enabled: bool
    repeat_period: str
    start_date: DateDict
    end_date: DateDict
    days_of_week: list[str]


@dataclass
class TimePeriod:
    enabled: bool
    repeat_period: str


from gshock_api.iolib.packet import Header, Payload, Protocol


class EventsIO:
    result: CancelableResult | None = None
    connection: ConnectionProtocol | None = None
    title: dict[str, object] | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol, event_number: int) -> CancelableResult:
        EventsIO.connection = connection
        # 30 is REMINDER_TITLE (0x30)
        await connection.request(f"{Protocol.REMINDER_TITLE.value:02X}{event_number}")  # reminder title
        # 31 is REMINDER_TIME (0x31)
        await connection.request(f"{Protocol.REMINDER_TIME.value:02X}{event_number}")  # reminder time
        EventsIO.result = CancelableResult[dict[str, object]]()
        return await EventsIO.result.get_result()

    @staticmethod
    async def send_to_watch_set(message: str) -> None:
        def reminder_title_from_json(reminder_json: dict[str, object]) -> bytearray:
            title_str = reminder_json.get("title", "")
            return to_byte_array(title_str, 18)

        def reminder_time_from_json(reminder_json: dict[str, object] | None) -> bytearray:
            def create_time_detail(repeat_period: str, start_date: DateDict, end_date: DateDict, days_of_week: list[str] | None) -> list[int]:
                def encode_date(time_detail: list[int], start_date: DateDict, end_date: DateDict) -> None:
                    class Month:
                        JANUARY = 1
                        FEBRUARY = 2
                        MARCH = 3
                        APRIL = 4
                        MAY = 5
                        JUNE = 6
                        JULY = 7
                        AUGUST = 8
                        SEPTEMBER = 9
                        OCTOBER = 10
                        NOVEMBER = 11
                        DECEMBER = 12

                        def __init__(self) -> None:
                            pass

                    def string_to_month(month_str: str) -> int:
                        months = {
                            "january": Month.JANUARY,
                            "february": Month.FEBRUARY,
                            "march": Month.MARCH,
                            "april": Month.APRIL,
                            "may": Month.MAY,
                            "june": Month.JUNE,
                            "july": Month.JULY,
                            "august": Month.AUGUST,
                            "september": Month.SEPTEMBER,
                            "october": Month.OCTOBER,
                            "november": Month.NOVEMBER,
                            "december": Month.DECEMBER,
                        }
                        return months.get(month_str.lower(), Month.JANUARY)

                    def hex_to_dec(hex_val: int) -> int:
                        return int(str(hex_val), 16)

                    time_detail[0] = hex_to_dec(start_date["year"] % 2000)
                    time_detail[1] = hex_to_dec(string_to_month(start_date["month"]))
                    time_detail[2] = hex_to_dec(start_date["day"])
                    time_detail[3] = hex_to_dec(end_date["year"] % 2000)
                    time_detail[4] = hex_to_dec(string_to_month(end_date["month"]))
                    time_detail[5] = hex_to_dec(end_date["day"])
                    time_detail[6], time_detail[7] = 0, 0

                time_detail = [0] * 8

                if repeat_period == "NEVER":
                    encode_date(time_detail, start_date, end_date)
                elif repeat_period == "WEEKLY":
                    encode_date(time_detail, start_date, end_date)

                    day_of_week = 0
                    if days_of_week is not None:
                        for day in days_of_week:
                            if day == "SUNDAY":
                                day_of_week |= ReminderMasks.SUNDAY_MASK
                            elif day == "MONDAY":
                                day_of_week |= ReminderMasks.MONDAY_MASK
                            elif day == "TUESDAY":
                                day_of_week |= ReminderMasks.TUESDAY_MASK
                            elif day == "WEDNESDAY":
                                day_of_week |= ReminderMasks.WEDNESDAY_MASK
                            elif day == "THURSDAY":
                                day_of_week |= ReminderMasks.THURSDAY_MASK
                            elif day == "FRIDAY":
                                day_of_week |= ReminderMasks.FRIDAY_MASK
                            elif day == "SATURDAY":
                                day_of_week |= ReminderMasks.SATURDAY_MASK

                    time_detail[6] = day_of_week
                    time_detail[7] = 0
                elif repeat_period in {"MONTHLY", "YEARLY"}:
                    encode_date(time_detail, start_date, end_date)
                else:
                    logger.debug(f"Cannot handle Repeat Period: {repeat_period}")

                return time_detail

            def create_time_period(enabled: bool, repeat_period: str) -> int:
                time_period = 0
                if enabled:
                    time_period |= ReminderMasks.ENABLED_MASK
                if repeat_period == "WEEKLY":
                    time_period |= ReminderMasks.WEEKLY_MASK
                elif repeat_period == "MONTHLY":
                    time_period |= ReminderMasks.MONTHLY_MASK
                elif repeat_period == "YEARLY":
                    time_period |= ReminderMasks.YEARLY_MASK
                return time_period

            enabled: bool = reminder_json.get("enabled", False)
            repeat_period: str = reminder_json.get("repeat_period", "")
            start_date: DateDict = reminder_json.get("start_date", {"year": 0, "month": "", "day": 0})
            end_date: DateDict = reminder_json.get("end_date", {"year": 0, "month": "", "day": 0})
            days_of_week: list[str] | None = reminder_json.get("days_of_week")

            reminder_cmd = bytearray()
            reminder_cmd += bytearray([create_time_period(enabled, repeat_period)])
            reminder_cmd += bytearray(create_time_detail(repeat_period, start_date, end_date, days_of_week))

            return reminder_cmd

        reminders_json_arr: list[dict[str, object]] | None = json.loads(message).get("value")
        if reminders_json_arr is None:
            reminders_json_arr = []

        for index, element in enumerate(reminders_json_arr):
            reminder_json: dict[str, object] = element
            title = reminder_title_from_json(reminder_json)

            # Reminder Title Packet = [0x30] + [index+1] + [title...]
            # Header protocol=0x30. Payload=[index+1] + [title...]
            
            payload_title = Payload(data=bytearray([index + 1]) + title)
            packet_bytes_title = bytearray([Protocol.REMINDER_TITLE.value]) + payload_title.data
            
            title_byte_arr_to_send = to_compact_string(to_hex_string(packet_bytes_title))

            if EventsIO.connection is None:
                raise RuntimeError("EventsIO.connection not set")

            await EventsIO.connection.write(0x000E, title_byte_arr_to_send)
            
            # Reminder Time Packet = [0x31] + [index+1] + [time...]
            
            time_data = reminder_time_from_json(reminder_json.get("time"))
            payload_time = Payload(data=bytearray([index + 1]) + time_data)
            packet_bytes_time = bytearray([Protocol.REMINDER_TIME.value]) + payload_time.data
            
            reminder_time_byte_arr_to_send = to_compact_string(to_hex_string(packet_bytes_time))

            await EventsIO.connection.write(0x000E, reminder_time_byte_arr_to_send)

    @staticmethod
    def on_received(message: bytes) -> None:
        data: str = to_hex_string(message)

        def reminder_time_to_json(reminder_str: str) -> str:
            def convert_array_list_to_json_array(array_list: list[object]) -> list[object]:
                return [item for item in array_list]

            def decode_time_period(time_period: int) -> TimePeriod:
                enabled = (time_period & ReminderMasks.ENABLED_MASK) == ReminderMasks.ENABLED_MASK
                if (time_period & ReminderMasks.WEEKLY_MASK) == ReminderMasks.WEEKLY_MASK:
                    repeat_period = "WEEKLY"
                elif (time_period & ReminderMasks.MONTHLY_MASK) == ReminderMasks.MONTHLY_MASK:
                    repeat_period = "MONTHLY"
                elif (time_period & ReminderMasks.YEARLY_MASK) == ReminderMasks.YEARLY_MASK:
                    repeat_period = "YEARLY"
                else:
                    repeat_period = "NEVER"
                return TimePeriod(enabled, repeat_period)

            def decode_time_detail(time_detail: list[int]) -> dict[str, object]:
                def decode_date(time_detail: list[int]) -> dict[str, object]:
                    def int_to_month_str(month_int: int) -> str:
                        months = [
                            "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
                            "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"
                        ]
                        if month_int < 1 or month_int > 12:
                            return ""
                        return months[month_int - 1]

                    date: dict[str, object] = {}
                    date["year"] = dec_to_hex(time_detail[0]) + 2000
                    date["month"] = int_to_month_str(dec_to_hex(time_detail[1]))
                    date["day"] = dec_to_hex(time_detail[2])
                    return date

                result: dict[str, object] = {}
                start_date = decode_date(time_detail[1:])
                result["start_date"] = start_date
                end_date = decode_date(time_detail[4:])
                result["end_date"] = end_date

                day_of_week = time_detail[7]
                days_of_week: list[str] = []
                if (day_of_week & ReminderMasks.SUNDAY_MASK) == ReminderMasks.SUNDAY_MASK:
                    days_of_week.append("SUNDAY")
                if (day_of_week & ReminderMasks.MONDAY_MASK) == ReminderMasks.MONDAY_MASK:
                    days_of_week.append("MONDAY")
                if (day_of_week & ReminderMasks.TUESDAY_MASK) == ReminderMasks.TUESDAY_MASK:
                    days_of_week.append("TUESDAY")
                if (day_of_week & ReminderMasks.WEDNESDAY_MASK) == ReminderMasks.WEDNESDAY_MASK:
                    days_of_week.append("WEDNESDAY")
                if (day_of_week & ReminderMasks.THURSDAY_MASK) == ReminderMasks.THURSDAY_MASK:
                    days_of_week.append("THURSDAY")
                if (day_of_week & ReminderMasks.FRIDAY_MASK) == ReminderMasks.FRIDAY_MASK:
                    days_of_week.append("FRIDAY")
                if (day_of_week & ReminderMasks.SATURDAY_MASK) == ReminderMasks.SATURDAY_MASK:
                    days_of_week.append("SATURDAY")
                result["days_of_week"] = days_of_week
                return result

            int_arr = to_int_array(reminder_str)
            if int_arr[3] == 0xFF:
                return json.dumps({"end": ""})

            reminder_all = to_int_array(reminder_str)
            reminder = reminder_all[2:]
            reminder_json: dict[str, object] = {}
            time_period = decode_time_period(reminder[0])
            reminder_json["enabled"] = time_period.enabled
            reminder_json["repeat_period"] = time_period.repeat_period

            time_detail_map = decode_time_detail(reminder)

            reminder_json["start_date"] = time_detail_map["start_date"]
            reminder_json["end_date"] = time_detail_map["end_date"]
            reminder_json["days_of_week"] = convert_array_list_to_json_array(time_detail_map["days_of_week"])

            return json.dumps({"time": reminder_json})

        reminder_json = json.loads(reminder_time_to_json(data[2:]))
        if EventsIO.title is not None:
            reminder_json.update(EventsIO.title)
        if EventsIO.result is None:
            raise RuntimeError("EventsIO.result is not set")
        EventsIO.result.set_result(reminder_json)

    @staticmethod
    def on_received_title(message: bytes) -> None:
        if EventsIO.title is None:
            EventsIO.title = {}
        EventsIO.title = ReminderDecoder.reminder_title_to_json(message)


class ReminderDecoder:
    @staticmethod
    def reminder_title_to_json(message: bytes) -> dict[str, str]:
        hex_str = to_hex_string(message)
        int_arr = to_int_array(hex_str)
        if int_arr[2] == 0xFF:
            return {"end": ""}
        reminder_json: dict[str, str] = {}
        reminder_json["title"] = clean_str(to_ascii_string(hex_str, 2))
        return reminder_json
