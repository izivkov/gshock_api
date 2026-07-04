from collections import ChainMap
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Final

type ModelCapability = dict[str, Any]
type ModelMap = dict[Any, ChainMap]


class WatchModel(IntEnum):
    GA = 1
    GW = 2
    DW = 3
    GMW = 4
    GPR = 5
    GST = 6
    MSG = 7
    GB001 = 8
    GBD = 9
    ECB = 10
    MRG = 11
    OCW = 12
    GB = 13
    GM = 14
    ABL = 15
    DW_H = 16
    UNKNOWN = 20


@dataclass
class WatchInfo:

    # Basic info
    name: str = ""
    short_name: str = ""
    address: str = ""
    model: WatchModel = WatchModel.UNKNOWN

    # Default capabilities
    default_cap: Final[ModelCapability] = field(default_factory=lambda: {
        "worldCitiesCount": 2,
        "dstCount": 3,
        "alarmCount": 5,
        "hasAutoLight": False,
        "hasReminders": False,
        "shortLightDuration": "",
        "longLightDuration": "",
        "weekLanguageSupported": True,
        "worldCities": True,
        "temperature": True,
        "batteryLevelLowerLimit": 15,
        "batteryLevelUpperLimit": 20,
        "alwaysConnected": False,
        "findButtonUserDefined": False,
        "hasPowerSavingMode": True,
        "hasDnD": False,
        "hasBatteryLevel": False,
        "hasWorldCities": True,
    })

    # The per-model overrides
    model_caps: list[ModelCapability] = field(default_factory=lambda: [
        {
            "model": WatchModel.GW,
            "worldCitiesCount": 6,
            "hasReminders": True,
            "shortLightDuration": "2s",
            "longLightDuration": "4s",
            "batteryLevelLowerLimit": 9,
            "batteryLevelUpperLimit": 19,
        },
        {
            "model": WatchModel.MRG,
            "worldCitiesCount": 6,
            "hasReminders": True,
            "shortLightDuration": "2s",
            "longLightDuration": "4s",
            "batteryLevelLowerLimit": 9,
            "batteryLevelUpperLimit": 19,
        },
        {
            "model": WatchModel.GMW,
            "worldCitiesCount": 6,
            "hasAutoLight": True,
            "hasReminders": True,
            "shortLightDuration": "2s",
            "longLightDuration": "4s",
        },
        {
            "model": WatchModel.GST,
            "worldCitiesCount": 2,
            "dstCount": 1,
            "hasWorldCities": False,
            "shortLightDuration": "1.5s",
            "longLightDuration": "3s",
        },
        {
            "model": WatchModel.GA,
            "worldCitiesCount": 2,
            "hasAutoLight": True,
            "hasReminders": True,
        },
        {
            "model": WatchModel.ABL,
            "worldCitiesCount": 2,
            "dstCount": 1,
            "hasWorldCities": False,
            "shortLightDuration": "1.5s",
            "longLightDuration": "3s",
        },
        {
            "model": WatchModel.GB001,
            "hasAutoLight": True,
        },
        {
            "model": WatchModel.MSG,
            "hasAutoLight": True,
            "hasReminders": True,
        },
        {
            "model": WatchModel.GPR,
            "hasAutoLight": True,
            "weekLanguageSupported": False,
        },
        {
            "model": WatchModel.DW,
            "hasAutoLight": True,
        },
        {
            "model": WatchModel.GBD,
            "hasAutoLight": True,
            "worldCities": False,
            "temperature": False,
            "alwaysConnected": True,
        },
        {
            "model": WatchModel.ECB,
            "hasAutoLight": True,
            "temperature": False,
            "alwaysConnected": True,
            "findButtonUserDefined": True,
            "hasPowerSavingMode": False,
            "hasDnD": True,
        },
        {
            "model": WatchModel.DW_H,
            "hasAutoLight": True,
            "temperature": False,
            "alwaysConnected": True,
            "findButtonUserDefined": True,
            "hasPowerSavingMode": False,
            "hasDnD": True,
        },
    ])

    # ChainMap lookup table
    model_map: ModelMap = field(init=False)

    def __post_init__(self) -> None:
        # Build the ChainMaps for each model
        self.model_map = {
            entry["model"]: ChainMap(entry, self.default_cap)
            for entry in self.model_caps
        }

        # Also ensure UNKNOWN uses defaults
        self.model_map.setdefault(
            WatchModel.UNKNOWN,
            ChainMap({}, self.default_cap)
        )

    #
    # --- Public API ---
    #

    def set_name_and_model(self, name: str) -> None:
        details = self._resolve_watch_details(name)
        if not details:
            return
        for key, value in details.items():
            setattr(self, key, value)

    def lookup_watch_info(self, name: str) -> ModelCapability | None:
        return self._resolve_watch_details(name)

    def _resolve_watch_details(self, name: str) -> ModelCapability | None:
        parts = name.split(" ")
        if len(parts) < 2:
            return None
        short_name = parts[1]

        # Model resolution
        if short_name in {"ECB-10", "ECB-20", "ECB-30"}:
            model = WatchModel.ECB
        elif short_name.startswith("ABL"):
            model = WatchModel.ABL
        elif short_name.startswith("GST"):
            model = WatchModel.GST
        else:
            prefix_map = [
                ("MSG", WatchModel.MSG),
                ("GPR", WatchModel.GPR),
                ("GM-B2100", WatchModel.GA),
                ("GBD", WatchModel.GBD),
                ("GMW", WatchModel.GMW),
                ("DW-H", WatchModel.DW_H),
                ("DW", WatchModel.DW),
                ("GA", WatchModel.GA),
                ("GB", WatchModel.GB),
                ("GM", WatchModel.GM),
                ("GW", WatchModel.GW),
                ("MRG", WatchModel.MRG),
                ("ABL", WatchModel.ABL),
            ]
            model = WatchModel.UNKNOWN
            for prefix, m in prefix_map:
                if short_name.startswith(prefix):
                    model = m
                    break

        cap = self.model_map.get(model)
        if cap is None:
            cap = self.model_map[WatchModel.UNKNOWN]

        # Return flattened capability dict
        return {
            "name": name,
            "short_name": short_name,
            "model": model,
            **cap,
        }

    def set_address(self, address: str) -> None:
        self.address = address

    def get_address(self) -> str:
        return self.address

    def get_model(self) -> WatchModel:
        return self.model

    def reset(self) -> None:
        self.address = ""
        self.name = ""
        self.short_name = ""
        self.model = WatchModel.UNKNOWN

watch_info: WatchInfo = WatchInfo()