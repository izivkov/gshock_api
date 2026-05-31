from dataclasses import dataclass


@dataclass(frozen=True)
class BLEAction:
    pass

@dataclass(frozen=True)
class Write(BLEAction):
    handle: int
    data: bytes

@dataclass(frozen=True)
class Read(BLEAction):
    handle: int
