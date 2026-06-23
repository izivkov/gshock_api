from dataclasses import dataclass
import json
from typing import TypedDict

from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.iolib.actions import BLEAction, Write
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.iolib.packet import Payload, Protocol
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
from gshock_api.pending_requests_registry import PendingRequestsRegistry

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


class EventsIOFunctional:
    """
    Pure functional events modules implementing Monoids.
    """

    @staticmethod
    def reminder_title_from_json(reminder_json: dict[str, object]) -> bytearray:
        title_str = reminder_json.get("title", "")
        return to_byte_array(title_str, 18)
    async def request(connection: ConnectionProtocol, event_number: int) -> CancelableResult:
        EventsIO.connection = connection
        # 30 is REMINDER_TITLE (0x30)
        await connection.request(f"{Protocol.REMINDER_TITLE.value:02X}{event_number}")  # reminder title
        # 31 is REMINDER_TIME (0x31)
        await connection.request(f"{Protocol.REMINDER_TIME.value:02X}{event_number}")  # reminder time
        EventsIO.result = CancelableResult[dict[str, object]]()
        # Register the pending request with unique name based on event number
        PendingRequestsRegistry.register(f"EventsIO_{event_number}", EventsIO.result)
        try:
            return await EventsIO.result.get_result()
        finally:
            # Unregister when complete (success or error)
            PendingRequestsRegistry.unregister(f"EventsIO_{event_number}")

    @staticmethod
    def reminder_time_from_json(reminder_json: dict[str, object] | None) -> bytearray:
        if reminder_json is None:
            reminder_json = {}

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

    @staticmethod
    def prepare_watch_commands_set(message_json: str) -> list[BLEAction]:
        reminders_json_arr: list[dict[str, object]] | None = json.loads(message_json).get("value")
        if reminders_json_arr is None:
            reminders_json_arr = []

        actions: list[BLEAction] = []
        for index, element in enumerate(reminders_json_arr):
            reminder_json: dict[str, object] = element
            title = EventsIOFunctional.reminder_title_from_json(reminder_json)

            payload_title = Payload(data=bytearray([index + 1]) + title)
            packet_bytes_title = bytes([Protocol.REMINDER_TITLE.value]) + bytes(payload_title.data)
            actions.append(Write(handle=0x000E, data=packet_bytes_title))

            time_data = EventsIOFunctional.reminder_time_from_json(reminder_json.get("time"))  # type: ignore
            payload_time = Payload(data=bytearray([index + 1]) + time_data)
            packet_bytes_time = bytes([Protocol.REMINDER_TIME.value]) + bytes(payload_time.data)
            actions.append(Write(handle=0x000E, data=packet_bytes_time))

        return actions

    @staticmethod
    def decode_time(reminder_str: str) -> dict[str, object]:
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
            return {"end": ""}

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

        return {"time": reminder_json}


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


class EventsIO:
    """
    Stateful backward-compatible wrapper.
    Acts as the interpreter for EventsIOFunctional commands.
    """
    result: CancelableResult | None = None
    connection: ConnectionProtocol | None = None
    title: dict[str, object] | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol, event_number: int) -> CancelableResult:
        EventsIO.connection = connection
        await connection.request(f"{Protocol.REMINDER_TITLE.value:02X}{event_number}")
        await connection.request(f"{Protocol.REMINDER_TIME.value:02X}{event_number}")
        EventsIO.result = CancelableResult[dict[str, object]]()
        return await EventsIO.result.get_result()

    @staticmethod
    async def send_to_watch_set(message: str) -> None:
        if EventsIO.connection is None:
            raise RuntimeError("EventsIO.connection not set")

        commands = EventsIOFunctional.prepare_watch_commands_set(message)
        for command in commands:
            if isinstance(command, Write):
                cmd_hex = to_compact_string(to_hex_string(command.data))
                await EventsIO.connection.write(0x000E, cmd_hex)

    @staticmethod
    def on_received(message: bytes) -> None:
        data: str = to_hex_string(message)
        reminder_json = EventsIOFunctional.decode_time(data[2:])

        if EventsIO.title is not None:
            reminder_json.update(EventsIO.title)
        if EventsIO.result is None:
            raise RuntimeError("EventsIO.result is not set")
        EventsIO.result.set_result(reminder_json)

    @staticmethod
    def on_received_title(message: bytes) -> None:
        EventsIO.title = ReminderDecoder.reminder_title_to_json(message)  # type: ignore[assignment]
