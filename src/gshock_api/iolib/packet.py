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
    SERVICE_DISCOVERY_MANAGER = 0x47
    CURRENT_TIME = 0x09
    SETTING_FOR_USER_PROFILE = 0x45
    SETTING_FOR_TARGET_VALUE = 0x43
    ALERT_LEVEL = 0x0A
    SETTING_FOR_ALM = 0x15
    SETTING_FOR_ALM2 = 0x16
    SETTING_FOR_BASIC = 0x13
    CURRENT_TIME_MANAGER = 0x39
    WORLD_CITIES = 0x1F
    REMINDER_TITLE = 0x30
    REMINDER_TIME = 0x31
    TIMER = 0x18
    ERROR = 0xFF
    UNKNOWN = 0x0A
    CMD_SET_TIMEMODE = 0x47
    FIND_PHONE = 0x0A

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
