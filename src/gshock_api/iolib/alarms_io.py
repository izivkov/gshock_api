import json
from typing import Protocol as TypingProtocol

from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.iolib.actions import BLEAction, Write
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.logger import logger
from gshock_api.model.alarms import (
    ALARM_CONSTANT_VALUE,
    CHARACTERISTICS,
    ENABLED_MASK,
    HOURLY_CHIME_MASK,
    alarms_inst,
)
from gshock_api.utils import to_compact_string, to_hex_string, to_int_array
from gshock_api.watch_info import WatchModel, watch_info

CHARACTERISTICS: dict[str, int] = CasioConstants.CHARACTERISTICS

# --- Protocols defining the expected interface for alarm logic ---

class AlarmDecoderProtocol(TypingProtocol):
    """Interface for decoding hexadecimal alarm strings into structured data."""
    def to_json(self, hex_str: str) -> dict[str, list[dict[str, object]]]:
        ...

class AlarmsInstProtocol(TypingProtocol):
    """Interface for managing the alarm state collection."""
    alarms: list[dict[str, object]]

    def clear(self) -> None:
        """Resets the internal alarm storage."""
        ...

    def add_alarms(self, alarms: list[dict[str, object]]) -> None:
        """Appends new alarms to the internal storage."""
        ...

# Typed references to the global singletons
alarms_inst_typed: AlarmsInstProtocol = alarms_inst  # type: ignore[assignment]


def require_int(alarm: dict[str, object], key: str) -> int:
    value = alarm.get(key)
    if isinstance(value, int):
        return value
    raise TypeError(f"Alarm field '{key}' must be an int, got {type(value).__name__}")


def encode_alarm_flag(alarm: dict[str, object]) -> int:
    flag = 0
    if alarm.get("enabled"):
        flag |= ENABLED_MASK
    if alarm.get("hasHourlyChime"):
        flag |= HOURLY_CHIME_MASK
    return flag


def encode_first_alarm(alarm_json: dict[str, object]) -> bytearray:
    return bytearray(
        [
            CHARACTERISTICS["CASIO_SETTING_FOR_ALM"],
            encode_alarm_flag(alarm_json),
            ALARM_CONSTANT_VALUE,
            require_int(alarm_json, "hour"),
            require_int(alarm_json, "minute"),
        ]
    )


def encode_secondary_alarms(alarms_json: list[dict[str, object]]) -> bytearray:
    if len(alarms_json) < 2:
        return bytearray()

    all_alarms = bytearray([CHARACTERISTICS["CASIO_SETTING_FOR_ALM2"]])
    for alarm in alarms_json[1:]:
        all_alarms += bytearray(
            [
                encode_alarm_flag(alarm),
                ALARM_CONSTANT_VALUE,
                require_int(alarm, "hour"),
                require_int(alarm, "minute"),
            ]
        )
    return all_alarms


class AlarmDecoder:
    def to_json(self, command: str) -> dict[str, list[dict[str, object]]]:
        json_response: dict[str, list[dict[str, object]]] = {}
        int_array: list[int] = to_int_array(command)
        alarms: list[dict[str, object]] = []

        if int_array[0] == CHARACTERISTICS["CASIO_SETTING_FOR_ALM"]:
            int_array.pop(0)
            alarms.append(self.create_json_alarm(int_array))
            json_response["ALARMS"] = alarms
        elif int_array[0] == CHARACTERISTICS["CASIO_SETTING_FOR_ALM2"]:
            int_array.pop(0)
            quarter_len = len(int_array) // 4
            subarrays = [
                int_array[:quarter_len],
                int_array[quarter_len : 2 * quarter_len],
                int_array[2 * quarter_len : 3 * quarter_len],
                int_array[3 * quarter_len :],
            ]
            for subarr in subarrays:
                if subarr:
                    alarms.append(self.create_json_alarm(subarr))
            json_response["ALARMS"] = alarms
        else:
            logger.warning(f"Unhandled Command {command}")

        return json_response

    def create_json_alarm(self, int_array: list[int]) -> dict[str, object]:
        flag = int_array[0]
        return {
            "enabled": bool(flag & ENABLED_MASK),
            "hasHourlyChime": bool(flag & HOURLY_CHIME_MASK),
            "hour": int_array[2],
            "minute": int_array[3],
        }


alarm_decoder = AlarmDecoder()
alarm_decoder_typed: AlarmDecoderProtocol = alarm_decoder  # type: ignore[assignment]


class AlarmsIOFunctional:
    """
    Pure functional core for alarm protocols.
    
    This class is 'Pure' because it contains no global state (no connection, no result).
    It functions as a pure mathematical transformation: Input (JSON/Dict) -> Output (Commands).
    """

    @staticmethod
    def prepare_watch_commands() -> list[BLEAction]:
        """
        Declarative Command Generator.
        
        Instead of performing IO, this returns a data-structure describing 
        the desired intent. This allows for 'Plan-then-Execute' decoupling.
        """
        return [
            Write(
                handle=0x000C,
                data=bytes([CHARACTERISTICS["CASIO_SETTING_FOR_ALM"]])
            ),
            Write(
                handle=0x000C,
                data=bytes([CHARACTERISTICS["CASIO_SETTING_FOR_ALM2"]])
            )
        ]

    @staticmethod
    def prepare_watch_commands_mtg_b3000() -> list[BLEAction]:
        return [
            Write(
                handle=0x000C,
                data=bytes([CHARACTERISTICS["CASIO_SETTING_FOR_ALM"]])
            )
        ]

    @staticmethod
    def prepare_watch_commands_set(message_json: str) -> list[BLEAction]:
        """
        Pure Data Mapper.

        Translates raw input into a structured instruction set (The Command Pattern).
        The mapping logic is deterministic: given the same input, it will ALWAYS
        return the same list of Write actions.
        """
        parsed: dict[str, object] = json.loads(message_json)
        alarms_json_arr: list[dict[str, object]] = parsed.get("value", [])  # type: ignore

        if not alarms_json_arr:
            return []

        alarm_casio0 = encode_first_alarm(alarms_json_arr[0])
        alarm_casio = encode_secondary_alarms(alarms_json_arr)

        return [
            Write(handle=0x000E, data=bytes(alarm_casio0)),
            Write(handle=0x000E, data=bytes(alarm_casio)),
        ]

    @staticmethod
    def prepare_watch_commands_set_mtg_b3000(message_json: str) -> list[BLEAction]:
        parsed: dict[str, object] = json.loads(message_json)
        alarms_json_arr: list[dict[str, object]] = parsed.get("value", [])  # type: ignore

        if not alarms_json_arr:
            return []

        return [Write(handle=0x000E, data=bytes(encode_first_alarm(alarms_json_arr[0])))]

    @staticmethod
    def parse_packet(data: bytes) -> list[dict[str, object]]:
        """
        Pure Parser.
        
        Maps bytes to domain models without side effects. It does not update 
        any singleton state directly, returning the data instead for the 
        IO shell to handle.
        """
        decoded_full = alarm_decoder_typed.to_json(to_hex_string(data))
        return decoded_full.get("ALARMS", [])



class AlarmsIO:
    """
    Impure 'Imperative Shell'.
    
    This class manages the side effects (I/O, network status, mutable singletons).
    It interprets the 'plans' created by AlarmsIOFunctional.
    """
    result: CancelableResult | None = None
    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol) -> CancelableResult:
        """Initializes the alarm fetch sequence."""
        AlarmsIO.connection = connection
        alarms_inst_typed.clear()
        await AlarmsIO._get_alarms(connection)
        if AlarmsIO.result is None:
            raise RuntimeError("AlarmsIO.result must not be None after _get_alarms")
        return AlarmsIO.result

    @staticmethod
    async def _get_alarms(connection: ConnectionProtocol) -> CancelableResult[list[dict[str, object]]]:
        """Sends the trigger message to start the alarm retrieval process."""
        await connection.send_message('{ "action": "GET_ALARMS"}')
        AlarmsIO.result = CancelableResult[list[dict[str, object]]]()
        return await AlarmsIO.result.get_result()

    @staticmethod
    async def send_to_watch(_: str = "") -> None:
        """Executes the command sequence to request current alarms from the watch."""
        if AlarmsIO.connection is None:
            raise RuntimeError("AlarmsIO.connection is not set")

        if watch_info.model == WatchModel.MTG_B3000:
            commands = AlarmsIOFunctional.prepare_watch_commands_mtg_b3000()
        else:
            commands = AlarmsIOFunctional.prepare_watch_commands()

        for command in commands:
            if isinstance(command, Write):
                alarm_command: str = to_compact_string(to_hex_string(command.data))
                await AlarmsIO.connection.write(command.handle, alarm_command)

    @staticmethod
    async def send_to_watch_set(message: str) -> None:
        """Executes the command sequence to update alarms on the watch."""
        if AlarmsIO.connection is None:
            raise RuntimeError("AlarmsIO.connection is not set")

        if watch_info.model == WatchModel.MTG_B3000:
            commands = AlarmsIOFunctional.prepare_watch_commands_set_mtg_b3000(message)
        else:
            commands = AlarmsIOFunctional.prepare_watch_commands_set(message)

        for command in commands:
            if isinstance(command, Write):
                alarm_command: str = to_compact_string(to_hex_string(command.data))
                await AlarmsIO.connection.write(command.handle, alarm_command)

    @staticmethod
    def on_received(data: bytes) -> None:
        """
        Callback for incoming BLE data. Accumulates fragmented alarm packets
        until the full set is received.
        """
        decoded_alarms = AlarmsIOFunctional.parse_packet(data)
        alarms_inst_typed.add_alarms(decoded_alarms)

        alarm_count_threshold = watch_info.alarmCount

        # Once all alarms are collected, resolve the async result
        if len(alarms_inst_typed.alarms) == alarm_count_threshold and AlarmsIO.result is not None:
            AlarmsIO.result.set_result(alarms_inst_typed.alarms)