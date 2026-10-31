import json

from gshock_api.cancelable_result import CancelableResult
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.iolib.packet import Protocol
from gshock_api.model.exercise_profile import ExerciseProfile

OPCODE = Protocol.SETTING_FOR_EXERCISE.value


def _bcd_le(bs: bytes) -> int:
    return sum(((x >> 4) * 10 + (x & 0xF)) * 100 ** i for i, x in enumerate(bs))


def _to_bcd_le(v: int, n: int) -> bytes:
    out = []
    for _ in range(n):
        v, r = divmod(v, 100)
        out.append(((r // 10) << 4) | (r % 10))
    return bytes(out)


def _invert(bs: bytes) -> bytes:
    return bytes(~x & 0xFF for x in bs)


class ExerciseIO:
    """Stateful wrapper following the same pattern as SettingsIO.

    Wire format (opcode 0x2D):
      2d 00 GG GG GG GG HH HH WW WW
      GG = step goal, packed BCD, low digits first
      HH = height, packed BCD, each byte bit-inverted
      WW = weight, packed BCD, each byte bit-inverted
    """

    result: CancelableResult[str] | None = None
    connection: ConnectionProtocol | None = None
    last_profile: ExerciseProfile | None = None

    @staticmethod
    def encode(profile: ExerciseProfile) -> bytes:
        return (
            bytes([OPCODE, 0])
            + _to_bcd_le(profile.step_goal, 4)
            + _invert(_to_bcd_le(profile.height, 2))
            + _invert(_to_bcd_le(profile.weight, 2))
        )

    @staticmethod
    def decode(payload: bytes) -> ExerciseProfile:
        if not payload or payload[0] != OPCODE:
            raise ValueError("not an exercise payload")
        return ExerciseProfile(
            step_goal=_bcd_le(payload[2:6]),
            height=_bcd_le(_invert(payload[6:8])),
            weight=_bcd_le(_invert(payload[8:10])),
        )

    @staticmethod
    def to_json(profile: ExerciseProfile) -> str:
        return json.dumps({
            "stepGoal": profile.step_goal,
            "height": profile.height,
            "weight": profile.weight,
        })

    @staticmethod
    async def request(connection: ConnectionProtocol) -> str:
        ExerciseIO.connection = connection
        ExerciseIO.result = CancelableResult[str]()
        await connection.request(f"{OPCODE:02X}")
        return await ExerciseIO.result.get_result()

    @staticmethod
    async def send_to_watch(_message: str) -> None:
        if ExerciseIO.connection is None:
            raise RuntimeError("ExerciseIO.connection is not set")
        ExerciseIO.result = CancelableResult[str]()
        await ExerciseIO.connection.request(f"{OPCODE:02X}")

    @staticmethod
    async def send_to_watch_set(message: str) -> None:
        if ExerciseIO.connection is None:
            raise RuntimeError("ExerciseIO.connection is not set")
        value = json.loads(message).get("value", {})
        current = ExerciseIO.last_profile or ExerciseProfile()
        profile = ExerciseProfile(
            step_goal=value.get("stepGoal", current.step_goal),
            height=value.get("height", current.height),
            weight=value.get("weight", current.weight),
        )
        await ExerciseIO.connection.write(0x000E, ExerciseIO.encode(profile).hex())

    @staticmethod
    def on_received(message: bytes) -> None:
        profile = ExerciseIO.decode(message)
        ExerciseIO.last_profile = profile
        # Unsolicited notifications have no pending request; just cache them.
        if ExerciseIO.result is not None:
            ExerciseIO.result.set_result(ExerciseIO.to_json(profile))
            