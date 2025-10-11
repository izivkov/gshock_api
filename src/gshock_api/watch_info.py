from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import IntEnum

class WatchModel(IntEnum):
    """Enum for watch models replacing WATCH_MODEL class"""
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
    """Information and capabilities of a G-Shock watch"""
    # Basic information
    name: str = ""
    shortName: str = ""
    address: str = ""
    model: WatchModel = WatchModel.UNKNOWN
    
    # Watch capabilities with defaults
    worldCitiesCount: int = 2
    dstCount: int = 3
    alarmCount: int = 5
    hasAutoLight: bool = False
    hasReminders: bool = False
    shortLightDuration: str = ""
    longLightDuration: str = ""
    weekLanguageSupported: bool = True
    worldCities: bool = True
    temperature: bool = True
    batteryLevelLowerLimit: int = 15
    batteryLevelUpperLimit: int = 20
    alwaysConnected: bool = False
    findButtonUserDefined: bool = False
    hasPowerSavingMode: bool = True
    hasDnD: bool = False
    hasBatteryLevel: bool = False
    hasWorldCities: bool = True

    # Model capability definitions (deduplicated)
    models: List[Dict] = field(default_factory=lambda: [
            {
                "model": WatchModel.GW,
                "worldCitiesCount": 6,
                "dstCount": 3,
                "alarmCount": 5,
                "hasAutoLight": False,
                "hasReminders": True,
                "shortLightDuration": "2s",
                "longLightDuration": "4s",
                "batteryLevelLowerLimit": 9,
                "batteryLevelUpperLimit": 19,
            },
            {
                "model": WatchModel.MRG,
                "worldCitiesCount": 6,
                "dstCount": 3,
                "alarmCount": 5,
                "hasAutoLight": False,
                "hasReminders": True,
                "shortLightDuration": "2s",
                "longLightDuration": "4s",
                "batteryLevelLowerLimit": 9,
                "batteryLevelUpperLimit": 19,
            },
            {
                "model": WatchModel.GMW,
                "worldCitiesCount": 6,
                "dstCount": 3,
                "alarmCount": 5,
                "hasAutoLight": True,
                "hasReminders": True,
                "shortLightDuration": "2s",
                "longLightDuration": "4s",
            },
            {
                "model": WatchModel.GST,
                "worldCitiesCount": 2,
                "dstCount": 1,
                "alarmCount": 5,
                "hasAutoLight": False,
                "hasReminders": False,
                "shortLightDuration": "1.5s",
                "longLightDuration": "3s",
                "hasWorldCities": False
            },
            {
                "model": WatchModel.GA,
                "worldCitiesCount": 2,
                "dstCount": 1,
                "alarmCount": 5,
                "hasAutoLight": True,
                "hasReminders": True,
                "shortLightDuration": "1.5s",
                "longLightDuration": "3s",
            },
            {
                "model": WatchModel.ABL,
                "worldCitiesCount": 2,
                "dstCount": 1,
                "alarmCount": 5,
                "hasAutoLight": False,
                "hasReminders": False,
                "shortLightDuration": "1.5s",
                "longLightDuration": "3s",
                "hasWorldCities": False
            },
            {
                "model": WatchModel.GB001,
                "worldCitiesCount": 2,
                "dstCount": 1,
                "alarmCount": 5,
                "hasAutoLight": True,
                "hasReminders": False,
                "shortLightDuration": "1.5s",
                "longLightDuration": "3s",
            },
            {
                "model": WatchModel.MSG,
                "worldCitiesCount": 2,
                "dstCount": 1,
                "alarmCount": 5,
                "hasAutoLight": True,
                "hasReminders": True,
                "shortLightDuration": "1.5s",
                "longLightDuration": "3s",
            },
            {
                "model": WatchModel.GPR,
                "worldCitiesCount": 2,
                "dstCount": 1,
                "alarmCount": 5,
                "hasAutoLight": True,
                "hasReminders": False,
                "shortLightDuration": "1.5s",
                "longLightDuration": "3s",
                "weekLanguageSupported": False,
            },
            {
                "model": WatchModel.DW,
                "worldCitiesCount": 2,
                "dstCount": 1,
                "alarmCount": 5,
                "hasAutoLight": True,
                "hasReminders": False,
                "shortLightDuration": "1.5s",
                "longLightDuration": "3s",
            },
            {
                "model": WatchModel.GBD,
                "worldCitiesCount": 2,
                "dstCount": 1,
                "alarmCount": 5,
                "hasAutoLight": True,
                "hasReminders": False,
                "shortLightDuration": "1.5s",
                "longLightDuration": "3s",
                "worldCities": False,
                "temperature": False,
                "alwaysConnected": True,
            },
            {
                "model": WatchModel.ECB,
                "worldCitiesCount": 2,
                "dstCount": 1,
                "alarmCount": 5,
                "hasAutoLight": True,
                "hasReminders": False,
                "shortLightDuration": "1.5s",
                "longLightDuration": "3s",
                "worldCities": True,
                "temperature": False,
                "hasBatteryLevel": False,
                "alwaysConnected": True,
                "findButtonUserDefined": True,
                "hasPowerSavingMode": False,
                "hasDnD": True
            },
            {
                "model": WatchModel.DW_H,
                "worldCitiesCount": 2,
                "dstCount": 1,
                "alarmCount": 5,
                "hasAutoLight": True,
                "hasReminders": False,
                "shortLightDuration": "1.5s",
                "longLightDuration": "3s",
                "worldCities": True,
                "temperature": False,
                "hasBatteryLevel": False,
                "alwaysConnected": True,
                "findButtonUserDefined": True,
                "hasPowerSavingMode": False,
                "hasDnD": True
            },
            {
                "model": WatchModel.UNKNOWN,
                "worldCitiesCount": 2,
                "dstCount": 1,
                "alarmCount": 5,
                "hasAutoLight": True,
                "hasReminders": False,
                "shortLightDuration": "1.5s",
                "longLightDuration": "3s",
            },
        ])
    
    def __post_init__(self) -> None:
        """Initialize model map after instance creation"""
        self.model_map = {entry["model"]: entry for entry in self.models}

    def set_name_and_model(self, name: str) -> None:
        """Set watch name and determine its model based on the name"""
        details = self._resolve_watch_details(name)
        if not details:
            return
        
        for key, value in details.items():
            setattr(self, key, value)

    def lookup_watch_info(self, name: str) -> Optional[Dict]:
        """Look up watch information based on name"""
        return self._resolve_watch_details(name)

    def _resolve_watch_details(self, name: str) -> Optional[Dict]:
        """Internal method to resolve watch details from name"""
        shortName = None
        model = WatchModel.UNKNOWN

        parts = name.split(" ")
        if len(parts) > 1:
            shortName = parts[1]
        if not shortName:
            return None

        # Model resolution logic
        if shortName in {"ECB-10", "ECB-20", "ECB-30"}:
            model = WatchModel.ECB
        elif shortName.startswith("ABL"):
            model = WatchModel.ABL
        elif shortName.startswith("GST"):
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
            for prefix, m in prefix_map:
                if shortName.startswith(prefix):
                    model = m
                    break

        # Get model info and compute details
        model_info = self.model_map.get(model, {})
        return {
            "name": name,
            "shortName": shortName,
            "model": model,
            "hasReminders": model_info.get("hasReminders", False),
            "hasAutoLight": model_info.get("hasAutoLight", False),
            "alarmCount": model_info.get("alarmCount", 0),
            "worldCitiesCount": model_info.get("worldCitiesCount", 0),
            "dstCount": model_info.get("dstCount", 0),
            "shortLightDuration": model_info.get("shortLightDuration", ""),
            "longLightDuration": model_info.get("longLightDuration", ""),
            "weekLanguageSupported": model_info.get("weekLanguageSupported", True),
            "worldCities": model_info.get("worldCities", True),
            "temperature": model_info.get("temperature", True),
            "batteryLevelLowerLimit": model_info.get("batteryLevelLowerLimit", 15),
            "batteryLevelUpperLimit": model_info.get("batteryLevelUpperLimit", 20),
            "alwaysConnected": model_info.get("alwaysConnected", False),
            "findButtonUserDefined": model_info.get("findButtonUserDefined", False),
            "hasPowerSavingMode": model_info.get("hasPowerSavingMode", False),
            "hasDnD": model_info.get("hasDnD", False),
            "hasBatteryLevel": model_info.get("hasBatteryLevel", False),
            "hasWorldCities": model_info.get("hasWorldCities", True),
        }

    def set_address(self, address: str) -> None:
        """Set the watch's address"""
        self.address = address

    def get_address(self) -> str:
        """Get the watch's address"""
        return self.address

    def get_model(self) -> WatchModel:
        """Get the watch's model"""
        return self.model

    def reset(self) -> None:
        """Reset watch information to defaults"""
        self.address = ""
        self.name = ""
        self.shortName = ""
        self.model = WatchModel.UNKNOWN

watch_info = WatchInfo()