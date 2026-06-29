from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Union


class Protocol(IntEnum):
    APP_INFO = 0x22
    WATCH_NAME = 0x23
    BLE_FEATURES = 0x10
    SETTING_FOR_BLE = 0x11
    ADVERTISE_PARAMETER_MANAGER = 0x3B
    CONNECTION_PARAMETER_MANAGER = 0x3A
    MODULE_ID = 0x26
    WATCH_CONDITION = 0x28
    VERSION_INFORMATION = 0x20
    DST_WATCH_STATE = 0x1D
    DST_SETTING = 0x1E
    CURRENT_TIME = 0x09
    SETTING_FOR_USER_PROFILE = 0x45
    SETTING_FOR_TARGET_VALUE = 0x43
    SETTING_FOR_ALM = 0x15
    SETTING_FOR_ALM2 = 0x16
    SETTING_FOR_BASIC = 0x13
    CURRENT_TIME_MANAGER = 0x39
    WORLD_CITIES = 0x1F
    REMINDER_TITLE = 0x30
    REMINDER_TIME = 0x31
    TIMER = 0x18
    HOME_TIME = 0x24
    ERROR = 0xFF

    # NOTE: The values below are shared aliases. Python's IntEnum will alias them
    # to the first enum member defined with that numeric value. They are kept for
    # readability and dispatcher-map lookup purposes; use the CHARACTERISTICS map
    # (not this enum) when the distinction between aliased names matters.
    SERVICE_DISCOVERY_MANAGER = 0x47
    CMD_SET_TIMEMODE = 0x47   # alias → SERVICE_DISCOVERY_MANAGER

    ALERT_LEVEL = 0x0A
    UNKNOWN = 0x0A            # alias → ALERT_LEVEL
    FIND_PHONE = 0x0A         # alias → ALERT_LEVEL


@dataclass
class Header:
    protocol: Protocol
    size: int

@dataclass
class Payload:
    data: bytearray

@dataclass
class Trailer:
    data: bytearray
    checksum: int

# Algebraic Data Type equivalent
Packet = Union[Header, Payload, Trailer]
