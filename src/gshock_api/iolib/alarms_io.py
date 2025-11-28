import json
from typing import Protocol

from gshock_api.alarms import alarm_decoder, alarms_inst
from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.utils import to_compact_string, to_hex_string

CHARACTERISTICS: dict[str, int] = CasioConstants.CHARACTERISTICS



class AlarmDecoderProtocol(Protocol):
    def to_json(self, hex_str: str) -> dict[str, list[dict[str, object]]]:
        ...


class AlarmsInstProtocol(Protocol):
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


class AlarmsIO:
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

        alarm_command: str = to_compact_string(
            to_hex_string(bytearray([CHARACTERISTICS["CASIO_SETTING_FOR_ALM"]]))
        )
        await AlarmsIO.connection.write(0x000C, alarm_command)

        alarm_command_2: str = to_compact_string(
            to_hex_string(bytearray([CHARACTERISTICS["CASIO_SETTING_FOR_ALM2"]]))
        )
        await AlarmsIO.connection.write(0x000C, alarm_command_2)

    @staticmethod
    async def send_to_watch_set(message: str) -> None:
        if AlarmsIO.connection is None:
            raise RuntimeError("AlarmsIO.connection is not set")

        parsed: dict[str, object] = json.loads(message)
        alarms_json_arr: list[dict[str, object]] = parsed.get("value", [])

        alarm_casio0: str = to_compact_string(
            to_hex_string(
                alarms_inst_typed.from_json_alarm_first_alarm(alarms_json_arr[0])
            )
        )
        await AlarmsIO.connection.write(0x000E, alarm_casio0)

        alarm_casio: str = to_compact_string(
            to_hex_string(
                alarms_inst_typed.from_json_alarm_secondary_alarms(alarms_json_arr)
            )
        )
        await AlarmsIO.connection.write(0x000E, alarm_casio)

    @staticmethod
    def on_received(data: bytes) -> None:
        decoded_full: dict[str, list[dict[str, object]]] = alarm_decoder_typed.to_json(
            to_hex_string(data)
        )
        decoded_alarms: list[dict[str, object]] = decoded_full["ALARMS"]
        alarms_inst_typed.add_alarms(decoded_alarms)

        ALARM_COUNT_THRESHOLD = 5

        if len(alarms_inst_typed.alarms) == ALARM_COUNT_THRESHOLD and AlarmsIO.result is not None:
            AlarmsIO.result.set_result(alarms_inst_typed.alarms)

