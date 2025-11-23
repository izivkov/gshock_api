from dataclasses import dataclass, field
from enum import IntEnum

# --- Type Aliases for Clarity ---
from typing import Any, Final, TypeAlias

# Type for a single model's capability dictionary.
# Keys are strings, values are the union of all primitive types and the WatchModel enum found in the model dictionary.
ModelCapability: TypeAlias = dict[str, Any | int | str | bool]  # type: ignore  # noqa: F821, UP040
ModelMap: TypeAlias = dict[Any, ModelCapability]  # type: ignore  # noqa: F821, UP040

class WatchModel(IntEnum):
    """Enum for watch models replacing WATCH_MODEL class"""
    # Using explicit types for better compatibility, though IntEnum handles this
    GA: Final[int] = 1  
    GW: Final[int] = 2
    DW: Final[int] = 3
    GMW: Final[int] = 4
    GPR: Final[int] = 5
    GST: Final[int] = 6
    MSG: Final[int] = 7
    GB001: Final[int] = 8
    GBD: Final[int] = 9
    ECB: Final[int] = 10
    MRG: Final[int] = 11
    OCW: Final[int] = 12
    GB: Final[int] = 13
    GM: Final[int] = 14
    ABL: Final[int] = 15
    DW_H: Final[int] = 16
    UNKNOWN: Final[int] = 20

@dataclass
class WatchInfo:
    """Information and capabilities of a G-Shock watch"""
    
    # Basic information
    name: str = ""
    shortName: str = ""  # noqa: N815
    address: str = ""
    model: WatchModel = WatchModel.UNKNOWN
    
    # Watch capabilities with defaults
    worldCitiesCount: int = 2  # noqa: N815
    dstCount: int = 3  # noqa: N815
    alarmCount: int = 5  # noqa: N815
    hasAutoLight: bool = False  # noqa: N815
    hasReminders: bool = False  # noqa: N815
    shortLightDuration: str = ""  # noqa: N815
    longLightDuration: str = ""  # noqa: N815
    weekLanguageSupported: bool = True  # noqa: N815
    worldCities: bool = True  # noqa: N815
    temperature: bool = True  
    batteryLevelLowerLimit: int = 15  # noqa: N815
    batteryLevelUpperLimit: int = 20  # noqa: N815
    alwaysConnected: bool = False  # noqa: N815
    findButtonUserDefined: bool = False  # noqa: N815
    hasPowerSavingMode: bool = True  # noqa: N815
    hasDnD: bool = False  # noqa: N815
    hasBatteryLevel: bool = False  # noqa: N815
    hasWorldCities: bool = True  # noqa: N815

    # Model capability definitions (Instance variable, requires field)
    # Using ModelCapability type alias for clarity and type safety
    models: list[ModelCapability] = field(default_factory=lambda: [
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
    
    # Instance variable to store the lookup map
    # Initialized in __post_init__
    model_map: ModelMap = field(init=False)

    def __post_init__(self) -> None:
        """Initialize model map after instance creation"""
        # Type enforcement on dictionary construction
        self.model_map = {
            entry["model"]: entry for entry in self.models
        } # type: ignore[misc] # Suppressing due to complex dict key type

    def set_name_and_model(self, name: str) -> None:
        """Set watch name and determine its model based on the name"""
        details: ModelCapability | None = self._resolve_watch_details(name)
        if not details:
            return
        
        # Dynamically set attributes on the instance
        for key, value in details.items():
            setattr(self, key, value)

    def lookup_watch_info(self, name: str) -> ModelCapability | None:
        """Look up watch information based on name"""
        return self._resolve_watch_details(name)

    def _resolve_watch_details(self, name: str) -> ModelCapability | None:
        """Internal method to resolve watch details from name"""
        shortName: str | None = None  # noqa: N806
        model: WatchModel = WatchModel.UNKNOWN

        parts: list[str] = name.split(" ")
        if len(parts) > 1:
            shortName = parts[1]  # noqa: N806
        if not shortName:
            return None

        # --- Model resolution logic ---
        if shortName in {"ECB-10", "ECB-20", "ECB-30"}:
            model = WatchModel.ECB
        elif shortName.startswith("ABL"):
            model = WatchModel.ABL
        elif shortName.startswith("GST"):
            model = WatchModel.GST
        else:
            # Type list of tuples for prefix mapping
            prefix_map: list[tuple[str, WatchModel]] = [
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
        model_info: ModelCapability = self.model_map.get(model, {})
        
        # Return the dictionary of attributes to be set on the instance
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

watch_info: WatchInfo = WatchInfo()