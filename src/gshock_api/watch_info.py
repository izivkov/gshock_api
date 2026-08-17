from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from gshock_api.protocols.analogue_protocol import AnalogueProtocol
from gshock_api.protocols.mip_protocol import MipProtocol
from gshock_api.protocols.standard_protocol import StandardProtocol
from gshock_api.protocols.watch_protocol import WatchProtocol


class WatchModel(Enum):
    GA = auto()
    GW = auto()
    DW_B5600 = auto()
    DW = auto()
    GMW = auto()
    GPR = auto()
    GST = auto()
    MSG = auto()
    GB001 = auto()
    GBD = auto()
    GBD_800 = auto()
    MRG_B5000 = auto()
    GCW_B5000 = auto()
    EQB = auto()
    ECB = auto()
    ABL_100 = auto()
    DW_H5600 = auto()
    GMW_BZ5000 = auto()
    GW_BX5600 = auto()
    MTG_B1000 = auto()
    MTG_B3000 = auto()
    GENERIC = auto()
    UNKNOWN = auto()  # Legacy fallback alias for GENERIC


# Standard protocol instances for ModelInfo defaults
STANDARD_PROTOCOL = StandardProtocol()
MIP_PROTOCOL = MipProtocol()
ANALOGUE_PROTOCOL = AnalogueProtocol()


@dataclass
class ModelInfo:
    model: WatchModel
    worldCitiesCount: int = 2
    dstCount: int = 1
    alarmCount: int = 5
    hasAutoLight: bool = False
    hasReminders: bool = False
    shortLightDuration: str = "1.5s"
    longLightDuration: str = "3s"
    weekLanguageSupported: bool = True
    worldCities: bool = True
    hasBatteryLevel: bool = True
    hasTemperature: bool = True
    batteryLevelLowerLimit: int = 9
    batteryLevelUpperLimit: int = 19
    alwaysConnected: bool = False
    findButtonUserDefined: bool = False
    hasPowerSavingMode: bool = True
    chimeInSettings: bool = False
    vibrate: bool = False
    hasHealthFunctions: bool = False
    hasMessages: bool = False
    hasDateFormat: bool = True
    hasWorldCities: bool = True
    hasHomeTime: bool = True
    hasMultipleFonts: bool = False
    hasStepCounter: bool = False
    hasStepCounterMock: bool = False
    hasNewTimeFormat: bool = False
    hasTimeAdjustment: bool = True
    hasSecondDial: bool = False
    hasFineWatchCondition: bool = False
    hasTimeFormat: bool = True
    hasHourlyChime: bool = True
    hasLongTimerKey: bool = False
    settingsSize: int = 17
    protocol: WatchProtocol = field(default_factory=lambda: STANDARD_PROTOCOL)


_MODEL_LIST: list[ModelInfo] = [
    ModelInfo(
        model=WatchModel.GW,
        worldCitiesCount=6, dstCount=3,
        hasAutoLight=True, hasReminders=True,
        shortLightDuration="2s", longLightDuration="4s",
        batteryLevelLowerLimit=9, batteryLevelUpperLimit=19,
        hasStepCounterMock=False,
    ),
    ModelInfo(
        model=WatchModel.DW_B5600,
        worldCitiesCount=6, dstCount=3,
        hasAutoLight=False, hasReminders=True,
        shortLightDuration="2s", longLightDuration="4s",
        batteryLevelLowerLimit=9, batteryLevelUpperLimit=19,
    ),
    ModelInfo(
        model=WatchModel.GMW_BZ5000,
        worldCitiesCount=6, dstCount=3,
        hasAutoLight=True, hasReminders=False,
        shortLightDuration="1.5s", longLightDuration="3s",
        batteryLevelLowerLimit=9, batteryLevelUpperLimit=19,
        hasMultipleFonts=True,
    ),
    ModelInfo(
        model=WatchModel.GW_BX5600,
        worldCitiesCount=6, dstCount=3,
        hasAutoLight=True, hasReminders=False,
        shortLightDuration="1.5s", longLightDuration="3s",
        batteryLevelLowerLimit=14, batteryLevelUpperLimit=24,
        hasMultipleFonts=True,
        hasNewTimeFormat=True,
        protocol=MIP_PROTOCOL,
    ),
    ModelInfo(
        model=WatchModel.MTG_B1000,
        worldCitiesCount=6, dstCount=3, alarmCount=1,
        hasAutoLight=True, hasReminders=True,
        shortLightDuration="2s", longLightDuration="4s",
        batteryLevelLowerLimit=9, batteryLevelUpperLimit=19,
        hasSecondDial=True,
        hasFineWatchCondition=True,
        hasHourlyChime=False,
        protocol=ANALOGUE_PROTOCOL,
    ),
    ModelInfo(
        model=WatchModel.MTG_B3000,
        worldCitiesCount=2, dstCount=1, alarmCount=1,
        hasAutoLight=False, hasReminders=False,
        shortLightDuration="1.5s", longLightDuration="3s",
        hasHomeTime=True,
        hasDateFormat=False, weekLanguageSupported=False,
        hasTimeFormat=False, settingsSize=12,
        batteryLevelLowerLimit=0, batteryLevelUpperLimit=100,
        hasSecondDial=True,
        hasFineWatchCondition=True,
        hasPowerSavingMode=False,
        hasHourlyChime=False,
        hasLongTimerKey=True,
        protocol=ANALOGUE_PROTOCOL,
    ),
    ModelInfo(
        model=WatchModel.MRG_B5000,
        worldCitiesCount=6, dstCount=3,
        hasAutoLight=True, hasReminders=True,
        shortLightDuration="2s", longLightDuration="4s",
        batteryLevelLowerLimit=9, batteryLevelUpperLimit=19,
    ),
    ModelInfo(
        model=WatchModel.GCW_B5000,
        worldCitiesCount=6, dstCount=3,
        hasAutoLight=True, hasReminders=True,
        shortLightDuration="2s", longLightDuration="4s",
        batteryLevelLowerLimit=9, batteryLevelUpperLimit=19,
    ),
    ModelInfo(
        model=WatchModel.GMW,
        worldCitiesCount=6, dstCount=3,
        hasAutoLight=True, hasReminders=True,
        shortLightDuration="2s", longLightDuration="4s",
        batteryLevelLowerLimit=9, batteryLevelUpperLimit=19,
    ),
    ModelInfo(model=WatchModel.GST, hasAutoLight=False, hasReminders=True),
    ModelInfo(
        model=WatchModel.ABL_100,
        hasAutoLight=False, hasReminders=False,
        hasTemperature=False, hasBatteryLevel=False,
        worldCities=False, hasWorldCities=False, hasHomeTime=False,
        hasStepCounter=True,
        hasDateFormat=False,
        weekLanguageSupported=False,
    ),
    ModelInfo(model=WatchModel.GA, hasAutoLight=False, hasReminders=True),
    ModelInfo(model=WatchModel.GB001, hasAutoLight=True, hasReminders=False),
    ModelInfo(model=WatchModel.MSG, hasAutoLight=False, hasReminders=True),
    ModelInfo(
        model=WatchModel.GPR,
        hasAutoLight=True, hasReminders=False, weekLanguageSupported=False,
    ),
    ModelInfo(
        model=WatchModel.DW_H5600,
        alarmCount=4,
        hasAutoLight=True, hasReminders=False,
        vibrate=True, chimeInSettings=True,
        findButtonUserDefined=True,
        shortLightDuration="1.5s", longLightDuration="5s",
        hasBatteryLevel=False, alwaysConnected=True, hasDateFormat=False,
        weekLanguageSupported=False,
        hasStepCounter=False,
    ),
    ModelInfo(model=WatchModel.DW, hasAutoLight=True, hasReminders=False),
    ModelInfo(
        model=WatchModel.GBD,
        hasAutoLight=True, hasReminders=False,
        worldCities=False, hasWorldCities=False, hasTemperature=False,
    ),
    ModelInfo(
        model=WatchModel.GBD_800,
        hasAutoLight=True, hasReminders=False,
        hasTemperature=False, hasBatteryLevel=False,
        worldCities=False, hasWorldCities=False, hasHomeTime=False,
    ),
    ModelInfo(
        model=WatchModel.EQB,
        hasAutoLight=True, hasReminders=False,
        worldCities=False, hasWorldCities=False, hasTemperature=False,
    ),
    ModelInfo(
        model=WatchModel.ECB,
        hasAutoLight=True, hasReminders=False,
        hasTemperature=False, hasBatteryLevel=False,
        alwaysConnected=True, findButtonUserDefined=True, hasPowerSavingMode=False,
    ),
    ModelInfo(model=WatchModel.GENERIC),
]

_MODEL_MAP: dict[WatchModel, ModelInfo] = {info.model: info for info in _MODEL_LIST}


EXACT_MODEL_MAP: dict[str, WatchModel] = {
    # Module 3452: GPR-B1000
    "GPR-B1000": WatchModel.GPR,
    # Module 3459: GMW-B5000, GW-B5000
    "GMW-B5000": WatchModel.GMW,
    "GW-B5000": WatchModel.GW,
    # Module 3461: GW-B5600, MRG-B5000
    "GW-B5600": WatchModel.GW,
    "MRG-B5000": WatchModel.GW,
    # Module 3464: GBD-800, GMD-B800
    "GBD-800": WatchModel.GBD_800,
    "GMD-B800": WatchModel.GBD_800,
    # Module 3475: GBD-H1000
    "GBD-H1000": WatchModel.GBD,
    # Module 3481: GBD-100
    "GBD-100": WatchModel.GBD,
    # Module 3482: GBX-100
    "GBX-100": WatchModel.GBD,
    # Module 3491: GSR-H1000
    "GSR-H1000": WatchModel.GENERIC,
    # Module 3506: GBD-200
    "GBD-200": WatchModel.GBD,
    # Module 3509: DW-B5600
    "DW-B5600": WatchModel.DW_B5600,
    # Module 3515: GBD-H2000, DW-GH5600
    "GBD-H2000": WatchModel.DW_H5600,
    "DW-GH5600": WatchModel.DW_H5600,
    # Module 3516: DW-H5600
    "DW-H5600": WatchModel.DW_H5600,
    # Module 3539: GMW-B5000#, GW-B5600#, MRG-B5000#, TRN-50, GCW-B5000, PRJ-BW002
    "GMW-B5000#": WatchModel.GCW_B5000,
    "GW-B5600#": WatchModel.GCW_B5000,
    "MRG-B5000#": WatchModel.GCW_B5000,
    "TRN-50": WatchModel.GCW_B5000,
    "GCW-B5000": WatchModel.GCW_B5000,
    "PRJ-BW002": WatchModel.GCW_B5000,
    # Module 3552 / 3520: GD-B500
    "GD-B500": WatchModel.GENERIC,
    # Module 3554: GPR-H1000
    "GPR-H1000": WatchModel.GPR,
    # Module 3565: ABL-100WE
    "ABL-100WE": WatchModel.ABL_100,
    "ABL-100": WatchModel.ABL_100,
    # Module 3568: GBD-300
    "GBD-300": WatchModel.GBD,
    # Module 3575: GMW-BZ5000
    "GMW-BZ5000": WatchModel.GMW_BZ5000,
    # Module 3577: GM-H5600
    "GM-H5600": WatchModel.DW_H5600,
    # Module 3586: GBX-H5600
    "GBX-H5600": WatchModel.GBD,
    # Module 3587: GDG-B100
    "GDG-B100": WatchModel.GBD,
    # Module 3599: GWF-300
    "GWF-300": WatchModel.GENERIC,
    # Module 5537: ECB-800
    "ECB-800": WatchModel.ECB,
    # Module 5554: GBA-800
    "GBA-800": WatchModel.GA,
    # Module 5582: ECB-900, ECB-950, GST-B200, GST-B300
    "ECB-900": WatchModel.GST,
    "ECB-950": WatchModel.GST,
    "GST-B200": WatchModel.GST,
    "GST-B300": WatchModel.GST,
    # Module 5588: GWR-B1000
    "GWR-B1000": WatchModel.GW,
    # Module 5594: GMC-B100
    "GMC-B100": WatchModel.GENERIC,
    # Module 5597: OCW-B1300
    "OCW-B1300": WatchModel.GENERIC,
    # Module 5602: PRT-B70
    "PRT-B70": WatchModel.GENERIC,
    # Module 5603: OCW-S5000
    "OCW-S5000": WatchModel.GENERIC,
    # Module 5604: EQB-1000
    "EQB-1000": WatchModel.EQB,
    # Module 5618: ECB-10
    "ECB-10": WatchModel.ECB,
    # Module 5623: GWF-A1000
    "GWF-A1000": WatchModel.GENERIC,
    # Module 5624: OCW-P2000
    "OCW-P2000": WatchModel.GENERIC,
    # Module 5636: MTG-B2000, MRG-BF1000
    "MTG-B2000": WatchModel.GENERIC,
    "MRG-BF1000": WatchModel.GENERIC,
    # Module 5641: GBA-900
    "GBA-900": WatchModel.GA,
    # Module 5657: GST-B400
    "GST-B400": WatchModel.GST,
    # Module 5672: MTG-B3000
    "MTG-B3000": WatchModel.MTG_B3000,
    # Module 5701: OCW-S7000
    "OCW-S7000": WatchModel.GENERIC,
    # Module 5713: GWG-B1000
    "GWG-B1000": WatchModel.GW,
    # Module 5728: OCW-S400
    "OCW-S400": WatchModel.GENERIC,
    # Module 5736: GA-B010
    "GA-B010": WatchModel.GA,
    # Module 5737 / 5725: GBA-950
    "GBA-950": WatchModel.GA,
    # Module 5744: GG-B100X
    "GG-B100X": WatchModel.GENERIC,
    # Module 5748 / 5631: GST-B1000
    "GST-B1000": WatchModel.GST,
    # Module 5712: EQB-1300
    "EQB-1300": WatchModel.EQB,
    # Module 5756 / 5775: GWR-B3000
    "GWR-B3000": WatchModel.GW,

    "GB-5600A": WatchModel.GA,
    "GB-6900A": WatchModel.GA,
    "GB-5600B": WatchModel.GA,
    "GB-6900B": WatchModel.GA,
    "GB-X6900B": WatchModel.GA,
    "GBA-400": WatchModel.GA,
    "GA-B2100": WatchModel.GA,
    "GM-B2100": WatchModel.GA,
    "GBM-2100": WatchModel.GA,
    "GA-B001": WatchModel.GA,
    "GST-B100": WatchModel.GST,
    "GST-B500": WatchModel.GST,
    "GST-B600": WatchModel.GST,
    "GST-W1000": WatchModel.GST,
    "MSG-B100": WatchModel.MSG,
    "G-B001": WatchModel.GB001,
    "EQB-500": WatchModel.EQB,
    "EQB-510": WatchModel.EQB,
    "EQB-600": WatchModel.EQB,
    "EQB-700": WatchModel.EQB,
    "EQB-501": WatchModel.EQB,
    "EQB-800": WatchModel.EQB,
    "EQB-900": WatchModel.EQB,
    "EQB-1100": WatchModel.EQB,
    "EQB-1200": WatchModel.EQB,
    "EQB-2000": WatchModel.EQB,
    "ECB-500": WatchModel.ECB,
    "ECB-20": WatchModel.ECB,
    "ECB-30": WatchModel.ECB,
    "ECB-40": WatchModel.ECB,
    "ECB-S100": WatchModel.ECB,
    "ECB-2000": WatchModel.ECB,
    "ECB-2300": WatchModel.ECB,
    "ECB-2200": WatchModel.ECB,
    "ECB-S10": WatchModel.ECB,
    "GW-BX5600": WatchModel.GW_BX5600,
    "MTG-B1000": WatchModel.MTG_B1000,
    "STB-1000": WatchModel.GENERIC,
    "SHB-100": WatchModel.GENERIC,
    "SHB-200": WatchModel.GENERIC,
    "GPW-2000": WatchModel.GENERIC,
    "GPW-G2000": WatchModel.GENERIC,
    "MRG-G2000": WatchModel.GENERIC,
    "OCW-G2000": WatchModel.GENERIC,
    "MRG-B1000": WatchModel.GENERIC,
    "LIW-B1000": WatchModel.GENERIC,
    "OCW-S4000": WatchModel.GENERIC,
    "OCW-T3000": WatchModel.GENERIC,
    "OCW-T4000": WatchModel.GENERIC,
    "OCW-T6000": WatchModel.GENERIC,
    "OCW-T4000A": WatchModel.GENERIC,
    "OCW-T4000B": WatchModel.GENERIC,
    "OCW-T4000C": WatchModel.GENERIC,
    "GR-B300": WatchModel.GENERIC,
    "MRG-B2100": WatchModel.GA,
    "GMC-B2100": WatchModel.GA,
    "OCW-SG1000": WatchModel.GENERIC,
    "MTG-B4000": WatchModel.GENERIC,
    "BSA-B100": WatchModel.GENERIC,
    "GMA-B800": WatchModel.GENERIC,
    "GR-B100": WatchModel.GENERIC,
    "GG-B100": WatchModel.GENERIC,
    "PRT-B50": WatchModel.GENERIC,
    "GR-B200": WatchModel.GENERIC,
    "OCW-T200": WatchModel.GENERIC,
    "OCW-B1200": WatchModel.GENERIC,
    "OCW-S6000": WatchModel.GENERIC,
    "OCW-T5000": WatchModel.GENERIC,
    "OCW-B1400": WatchModel.GENERIC,
    "MRG-B2000": WatchModel.GENERIC,
    "PRJ-B001": WatchModel.GB001,
    "OCW-5700": WatchModel.GENERIC,
    "MTG-B3100": WatchModel.MTG_B3000,
    "OCW-5800": WatchModel.GENERIC,
    "PRW-B1000": WatchModel.GENERIC,
    "GMD-B300": WatchModel.GENERIC,
    "WS-B1000": WatchModel.GENERIC,
    "F-B100W": WatchModel.GENERIC,
    "OCW-P3000": WatchModel.GENERIC,
}


def derive_short_name(name: str) -> str:
    """Derives short watch name by stripping 'CASIO ' and returning first word."""
    clean = name.removeprefix("CASIO ").strip()
    parts = clean.split(" ")
    return parts[0] if parts else ""


def resolve_model(name: str) -> WatchModel:
    """Resolves WatchModel via exact lookup in official Casio model map."""
    model_name = name.removeprefix("CASIO ").strip()
    return EXACT_MODEL_MAP.get(model_name, WatchModel.GENERIC)


def resolve_model_info(model: WatchModel) -> ModelInfo:
    """Looks up ModelInfo for model, falling back to GENERIC."""
    return _MODEL_MAP.get(model, _MODEL_MAP[WatchModel.GENERIC])


class WatchInfo:
    """Tracks characteristics and capabilities of the currently connected watch."""

    def __init__(self) -> None:
        self.name: str = ""
        self.short_name: str = ""
        self.address: str = ""
        self.model: WatchModel = WatchModel.GENERIC
        self.info: ModelInfo = resolve_model_info(WatchModel.GENERIC)

    def set_name_and_model(self, name: str) -> None:
        self.name = name
        self.short_name = derive_short_name(name)
        self.model = resolve_model(name)
        self.info = resolve_model_info(self.model)

    def lookup_watch_info(self, name: str) -> dict[str, Any]:
        short_name = derive_short_name(name)
        model = resolve_model(name)
        info = resolve_model_info(model)
        return {
            "name": name,
            "short_name": short_name,
            "model": model,
            "alwaysConnected": info.alwaysConnected,
            "worldCitiesCount": info.worldCitiesCount,
            "dstCount": info.dstCount,
            "alarmCount": info.alarmCount,
            "hasAutoLight": info.hasAutoLight,
            "hasReminders": info.hasReminders,
            "hasStepCounter": info.hasStepCounter,
            "hasNewTimeFormat": info.hasNewTimeFormat,
            "hasSecondDial": info.hasSecondDial,
        }

    def set_address(self, address: str) -> None:
        self.address = address

    def get_address(self) -> str:
        return self.address

    def get_model(self) -> WatchModel:
        return self.model

    def reset(self) -> None:
        self.name = ""
        self.short_name = ""
        self.address = ""
        self.model = WatchModel.GENERIC
        self.info = resolve_model_info(WatchModel.GENERIC)

    # Capability properties forwarded from self.info
    @property
    def worldCitiesCount(self) -> int:
        return self.info.worldCitiesCount

    @property
    def dstCount(self) -> int:
        return self.info.dstCount

    @property
    def alarmCount(self) -> int:
        return self.info.alarmCount

    @property
    def hasAutoLight(self) -> bool:
        return self.info.hasAutoLight

    @property
    def hasReminders(self) -> bool:
        return self.info.hasReminders

    @property
    def shortLightDuration(self) -> str:
        return self.info.shortLightDuration

    @property
    def longLightDuration(self) -> str:
        return self.info.longLightDuration

    @property
    def weekLanguageSupported(self) -> bool:
        return self.info.weekLanguageSupported

    @property
    def worldCities(self) -> bool:
        return self.info.worldCities

    @property
    def hasWorldCities(self) -> bool:
        return self.info.hasWorldCities

    @property
    def hasTemperature(self) -> bool:
        return self.info.hasTemperature

    @property
    def temperature(self) -> bool:
        return self.info.hasTemperature

    @property
    def hasBatteryLevel(self) -> bool:
        return self.info.hasBatteryLevel

    @property
    def batteryLevelLowerLimit(self) -> int:
        return self.info.batteryLevelLowerLimit

    @property
    def batteryLevelUpperLimit(self) -> int:
        return self.info.batteryLevelUpperLimit

    @property
    def alwaysConnected(self) -> bool:
        return self.info.alwaysConnected

    @property
    def findButtonUserDefined(self) -> bool:
        return self.info.findButtonUserDefined

    @property
    def hasPowerSavingMode(self) -> bool:
        return self.info.hasPowerSavingMode

    @property
    def chimeInSettings(self) -> bool:
        return self.info.chimeInSettings

    @property
    def vibrate(self) -> bool:
        return self.info.vibrate

    @property
    def hasHealthFunctions(self) -> bool:
        return self.info.hasHealthFunctions

    @property
    def hasMessages(self) -> bool:
        return self.info.hasMessages

    @property
    def hasDateFormat(self) -> bool:
        return self.info.hasDateFormat

    @property
    def hasHomeTime(self) -> bool:
        return self.info.hasHomeTime

    @property
    def hasMultipleFonts(self) -> bool:
        return self.info.hasMultipleFonts

    @property
    def hasStepCounter(self) -> bool:
        return self.info.hasStepCounter

    @property
    def hasStepCounterMock(self) -> bool:
        return self.info.hasStepCounterMock

    @property
    def hasNewTimeFormat(self) -> bool:
        return self.info.hasNewTimeFormat

    @property
    def hasTimeAdjustment(self) -> bool:
        return self.info.hasTimeAdjustment

    @property
    def hasSecondDial(self) -> bool:
        return self.info.hasSecondDial

    @property
    def hasFineWatchCondition(self) -> bool:
        return self.info.hasFineWatchCondition

    @property
    def hasTimeFormat(self) -> bool:
        return self.info.hasTimeFormat

    @property
    def hasHourlyChime(self) -> bool:
        return self.info.hasHourlyChime

    @property
    def hasLongTimerKey(self) -> bool:
        return self.info.hasLongTimerKey

    @property
    def settingsSize(self) -> int:
        return self.info.settingsSize

    @property
    def protocol(self) -> WatchProtocol:
        return self.info.protocol

    def __getattr__(self, item: str) -> Any:
        # Fallback to ModelInfo attribute lookup if present
        if hasattr(self.info, item):
            return getattr(self.info, item)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{item}'")


watch_info: WatchInfo = WatchInfo()