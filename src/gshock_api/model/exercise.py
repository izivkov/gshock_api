"""Exercise/profile data exchanged between an app and the watch.

The model contains no connection or persistence state. Apps supply an Exercise
instance and receive the same type back from ExerciseIO.
"""
from dataclasses import dataclass
import json

OPCODE = 0x2D


def _bcd_le(bs: bytes) -> int:
    return sum(((x >> 4) * 10 + (x & 0xF)) * 100 ** i for i, x in enumerate(bs))


def _to_bcd_le(v: int, n: int) -> bytes:
    out = []
    for _ in range(n):
        v, r = divmod(v, 100)
        out.append(((r // 10) << 4) | (r % 10))
    return bytes(out)


@dataclass(frozen=True)
class Exercise:
    """F-B100W exercise profile: daily step goal, height, and weight."""

    step_goal: int = 10000
    height: int = 0
    weight: int = 0

    @classmethod
    def decode(cls, payload: bytes) -> "Exercise":
        if len(payload) < 10 or payload[0] != OPCODE:
            raise ValueError("not an exercise payload")
        return cls(
            step_goal=_bcd_le(payload[2:6]),
            height=_bcd_le(bytes(~x & 0xFF for x in payload[6:8])),
            weight=_bcd_le(bytes(~x & 0xFF for x in payload[8:10])),
        )

    def encode(self) -> bytes:
        # class, reserved byte, goal (4), height (2), weight (2)
        return bytes([OPCODE, 0]) + \
            _to_bcd_le(self.step_goal, 4) + \
            bytes(~x & 0xFF for x in _to_bcd_le(self.height, 2)) + \
            bytes(~x & 0xFF for x in _to_bcd_le(self.weight, 2))

    @classmethod
    def from_json(cls, message: str) -> "Exercise":
        value = json.loads(message).get("value", {})
        return cls(
            step_goal=int(value["stepGoal"]),
            height=int(value["height"]),
            weight=int(value["weight"]),
        )

    def to_json(self) -> str:
        return json.dumps({
            "stepGoal": self.step_goal,
            "height": self.height,
            "weight": self.weight,
        })
