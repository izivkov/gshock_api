import json
from typing import Protocol as TypingProtocol

from gshock_api.alarms import alarm_decoder, alarms_inst
from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.iolib.actions import BLEAction, Write
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.utils import to_compact_string, to_hex_string

CHARACTERISTICS: dict[str, int] = CasioConstants.CHARACTERISTICS


class AlarmDecoderProtocol(TypingProtocol):
    def to_json(self, hex_str: str) -> dict[str, list[dict[str, object]]]:
        ...


class AlarmsInstProtocol(TypingProtocol):
    alarms: list[dict[str, object]]

    def clear(self) -> None:
        ...

    def add_alarms(self, alarms: list[dict[str, object]]) -> None:
        ...

    def from_json_alarm_first_alarm(self, alarm_json: dict[str, object]) -> bytes:
        ...

    def from_json_alarm_secondary_alarms(self, alarms_json: list[dict[str, object]]) -> bytes:
        ...


alarm_decoder_typed: AlarmDecoderProtocol = alarm_decoder  # type: ignore[assignment]
alarms_inst_typed: AlarmsInstProtocol = alarms_inst  # type: ignore[assignment]


class AlarmsIOFunctional:
    """
    Pure functional alarms modules implementing Monoids.
    """

    @staticmethod
    def prepare_watch_commands() -> list[BLEAction]:
        """
        Pure command generator (Monoid B) to request alarms from watch.
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
    def prepare_watch_commands_set(message_json: str) -> list[BLEAction]:
        """
        Pure command generator (Monoid B) to write alarms to watch.
        """
        parsed: dict[str, object] = json.loads(message_json)
        alarms_json_arr: list[dict[str, object]] = parsed.get("value", [])  # type: ignore

        alarm_casio0 = alarms_inst_typed.from_json_alarm_first_alarm(alarms_json_arr[0])
        alarm_casio = alarms_inst_typed.from_json_alarm_secondary_alarms(alarms_json_arr)

        return [
            Write(handle=0x000E, data=bytes(alarm_casio0)),
            Write(handle=0x000E, data=bytes(alarm_casio))
        ]

    @staticmethod
    def parse_packet(data: bytes) -> list[dict[str, object]]:
        """
        Pure parser for incoming alarm packet.
        """
        decoded_full = alarm_decoder_typed.to_json(to_hex_string(data))
        return decoded_full.get("ALARMS", [])


class AlarmsIO:
    """
    Stateful backward-compatible wrapper.
    Acts as the interpreter for functional commands.
    """
    result: CancelableResult | None = None
    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol) -> CancelableResult:
        AlarmsIO.connection = connection
        alarms_inst_typed.clear()
        await AlarmsIO._get_alarms(connection)
        if AlarmsIO.result is None:
            raise RuntimeError("AlarmsIO.result must not be None after _get_alarms")
        return AlarmsIO.result

    @staticmethod
    async def _get_alarms(connection: ConnectionProtocol) -> CancelableResult[list[dict[str, object]]]:
        await connection.send_message('{ "action": "GET_ALARMS"}')
        AlarmsIO.result = CancelableResult[list[dict[str, object]]]()
        return await AlarmsIO.result.get_result()

    @staticmethod
    async def send_to_watch(_: str = "") -> None:
        if AlarmsIO.connection is None:
            raise RuntimeError("AlarmsIO.connection is not set")

        commands = AlarmsIOFunctional.prepare_watch_commands()
        for command in commands:
            if isinstance(command, Write):
                alarm_command: str = to_compact_string(to_hex_string(command.data))
                await AlarmsIO.connection.write(command.handle, alarm_command)

    @staticmethod
    async def send_to_watch_set(message: str) -> None:
        if AlarmsIO.connection is None:
            raise RuntimeError("AlarmsIO.connection is not set")

        commands = AlarmsIOFunctional.prepare_watch_commands_set(message)
        for command in commands:
            if isinstance(command, Write):
                alarm_command: str = to_compact_string(to_hex_string(command.data))
                await AlarmsIO.connection.write(command.handle, alarm_command)

    @staticmethod
    def on_received(data: bytes) -> None:
        decoded_alarms = AlarmsIOFunctional.parse_packet(data)
        alarms_inst_typed.add_alarms(decoded_alarms)

        ALARM_COUNT_THRESHOLD = 5

        if len(alarms_inst_typed.alarms) == ALARM_COUNT_THRESHOLD and AlarmsIO.result is not None:
            AlarmsIO.result.set_result(alarms_inst_typed.alarms)
