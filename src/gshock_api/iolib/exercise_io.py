"""F-B100W exercise setting (opcode 0x2D): step goal, height, weight.

Layout (validated against official-app capture, 2026-10-04):
  2d 00 GG GG GG GG HH HH WW WW
  GG = step goal, packed BCD, low digits first (LE digit pairs)
  HH = height, same BCD, each byte bit-inverted
  WW = weight, same BCD, bit-inverted
"""
import json

from gshock_api.cancelable_result import CancelableResult
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.iolib.packet import Protocol

OPCODE = Protocol.SETTING_FOR_EXERCISE.value


def _bcd_le(bs: bytes) -> int:
    return sum(((x >> 4) * 10 + (x & 0xF)) * 100 ** i for i, x in enumerate(bs))


def _to_bcd_le(v: int, n: int) -> bytes:
    out = []
    for _ in range(n):
        v, r = divmod(v, 100)
        out.append(((r // 10) << 4) | (r % 10))
    return bytes(out)


class ExerciseProfile:
    def __init__(self, step_goal: int = 10000, height: int = 0, weight: int = 0):
        self.step_goal = step_goal
        self.height = height
        self.weight = weight

    @classmethod
    def decode(cls, payload: bytes) -> "ExerciseProfile":
        if not payload or payload[0] != OPCODE:
            raise ValueError("not an exercise payload")
        return cls(
            step_goal=_bcd_le(payload[2:6]),
            height=_bcd_le(bytes(~x & 0xFF for x in payload[6:8])),
            weight=_bcd_le(bytes(~x & 0xFF for x in payload[8:10])),
        )

    def encode(self) -> bytes:
        # 10 bytes total: class, 0x00, goal (4), height (2), weight (2)
        return bytes([OPCODE, 0]) + \
            _to_bcd_le(self.step_goal, 4) + \
            bytes(~x & 0xFF for x in _to_bcd_le(self.height, 2)) + \
            bytes(~x & 0xFF for x in _to_bcd_le(self.weight, 2))

    def to_json(self) -> str:
        return json.dumps({
            "stepGoal": self.step_goal,
            "height": self.height,
            "weight": self.weight,
        })


class ExerciseIO:
    """Stateful wrapper following the same pattern as SettingsIO."""

    result: CancelableResult[str] | None = None
    connection: ConnectionProtocol | None = None
    last_profile: ExerciseProfile | None = None

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
        await ExerciseIO.connection.write(0x000E, profile.encode().hex())

    @staticmethod
    def on_received(message: bytes) -> None:
        profile = ExerciseProfile.decode(message)
        ExerciseIO.last_profile = profile
        if ExerciseIO.result is None:
            raise RuntimeError("ExerciseIO.result is not set")
        ExerciseIO.result.set_result(profile.to_json())
