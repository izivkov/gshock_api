import json
from typing import Protocol as TypingProtocol

from gshock_api.alarms import alarm_decoder, alarms_inst
from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.iolib.actions import BLEAction, Write
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.utils import to_compact_string, to_hex_string
from gshock_api.pending_requests_registry import PendingRequestsRegistry

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

    def from_json_alarm_first_alarm(self, alarm_json: dict[str, object]) -> bytes:
        """Encodes the primary alarm configuration into bytes."""
        ...

    def from_json_alarm_secondary_alarms(self, alarms_json: list[dict[str, object]]) -> bytes:
        """Encodes remaining alarm configurations into bytes."""
        ...

# Typed references to the global singletons
alarm_decoder_typed: AlarmDecoderProtocol = alarm_decoder  # type: ignore[assignment]
alarms_inst_typed: AlarmsInstProtocol = alarms_inst  # type: ignore[assignment]


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
                handle=CasioConstants.HANDLE_READ_ALL_FEATURES,
                data=bytes([CHARACTERISTICS["CASIO_SETTING_FOR_ALM"]])
            ),
            Write(
                handle=CasioConstants.HANDLE_READ_ALL_FEATURES,
                data=bytes([CHARACTERISTICS["CASIO_SETTING_FOR_ALM2"]])
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

        # Transformation logic is isolated here, away from side-effecting code
        alarm_casio0 = alarms_inst_typed.from_json_alarm_first_alarm(alarms_json_arr[0])
        alarm_casio = alarms_inst_typed.from_json_alarm_secondary_alarms(alarms_json_arr)

        return [
            Write(handle=CasioConstants.HANDLE_ALL_FEATURES_WRITE, data=bytes(alarm_casio0)),
            Write(handle=CasioConstants.HANDLE_ALL_FEATURES_WRITE, data=bytes(alarm_casio))
        ]

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
    async def request(connection: ConnectionProtocol) -> list[dict[str, object]]:
        """Sends the trigger message and waits for the full alarm set to arrive."""
        AlarmsIO.connection = connection
        alarms_inst_typed.clear()
        await connection.send_message('{ "action": "GET_ALARMS"}')
        AlarmsIO.result = CancelableResult[list[dict[str, object]]]()
        # Register the pending request
        PendingRequestsRegistry.register("AlarmsIO", AlarmsIO.result)
        try:
            return await AlarmsIO.result.get_result()
        finally:
            # Unregister when complete (success or error)
            PendingRequestsRegistry.unregister("AlarmsIO")

    @staticmethod
    async def send_to_watch(_: str = "") -> None:
        """Executes the command sequence to request current alarms from the watch."""
        if AlarmsIO.connection is None:
            raise RuntimeError("AlarmsIO.connection is not set")

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

        ALARM_COUNT_THRESHOLD = 5

        # Once all alarms are collected, resolve the async result
        if len(alarms_inst_typed.alarms) == ALARM_COUNT_THRESHOLD and AlarmsIO.result is not None:
            AlarmsIO.result.set_result(alarms_inst_typed.alarms)