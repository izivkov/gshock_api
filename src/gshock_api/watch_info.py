from gshock_api.logger import logger

class WATCH_MODEL:
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

class WatchInfo:
    def __init__(self):
        self.name = ""
        self.shortName = ""
        self.address = ""
        self.model = WATCH_MODEL.UNKNOWN

        # Default capabilities
        self.worldCitiesCount = 2
        self.dstCount = 3
        self.alarmCount = 5
        self.hasAutoLight = False
        self.hasReminders = False
        self.shortLightDuration = ""
        self.longLightDuration = ""
        self.weekLanguageSupported = True
        self.worldCities = True
        self.temperature = True
        self.batteryLevelLowerLimit = 15
        self.batteryLevelUpperLimit = 20

        self.alwaysConnected = False
        self.findButtonUserDefined = False
        self.hasPowerSavingMode = True
        self.hasDnD = False
        self.hasBatteryLevel = False
        self.hasWorldCities = True

        # Model capability definitions (deduplicated)
        self.models = [
            {
                "model": WATCH_MODEL.GW,
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
                "model": WATCH_MODEL.MRG,
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
                "model": WATCH_MODEL.GMW,
                "worldCitiesCount": 6,
                "dstCount": 3,
                "alarmCount": 5,
                "hasAutoLight": True,
                "hasReminders": True,
                "shortLightDuration": "2s",
                "longLightDuration": "4s",
            },
            {
                "model": WATCH_MODEL.GST,
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
                "model": WATCH_MODEL.GA,
                "worldCitiesCount": 2,
                "dstCount": 1,
                "alarmCount": 5,
                "hasAutoLight": True,
                "hasReminders": True,
                "shortLightDuration": "1.5s",
                "longLightDuration": "3s",
            },
            {
                "model": WATCH_MODEL.ABL,
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
                "model": WATCH_MODEL.GB001,
                "worldCitiesCount": 2,
                "dstCount": 1,
                "alarmCount": 5,
                "hasAutoLight": True,
                "hasReminders": False,
                "shortLightDuration": "1.5s",
                "longLightDuration": "3s",
            },
            {
                "model": WATCH_MODEL.MSG,
                "worldCitiesCount": 2,
                "dstCount": 1,
                "alarmCount": 5,
                "hasAutoLight": True,
                "hasReminders": True,
                "shortLightDuration": "1.5s",
                "longLightDuration": "3s",
            },
            {
                "model": WATCH_MODEL.GPR,
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
                "model": WATCH_MODEL.DW,
                "worldCitiesCount": 2,
                "dstCount": 1,
                "alarmCount": 5,
                "hasAutoLight": True,
                "hasReminders": False,
                "shortLightDuration": "1.5s",
                "longLightDuration": "3s",
            },
            {
                "model": WATCH_MODEL.GBD,
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
                "model": WATCH_MODEL.ECB,
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
                "model": WATCH_MODEL.DW_H,
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
                "model": WATCH_MODEL.UNKNOWN,
                "worldCitiesCount": 2,
                "dstCount": 1,
                "alarmCount": 5,
                "hasAutoLight": True,
                "hasReminders": False,
                "shortLightDuration": "1.5s",
                "longLightDuration": "3s",
            },
        ]

        # Build model→info lookup
        self.model_map = {entry["model"]: entry for entry in self.models}

    def set_name_and_model(self, name):
        details = self._resolve_watch_details(name)
        if not details:
            return
        
        # Persist fields
        self.name                  = details["name"]
        self.shortName             = details["shortName"]
        self.model                 = details["model"]
        self.hasReminders          = details["hasReminders"]
        self.hasAutoLight          = details["hasAutoLight"]
        self.alarmCount            = details["alarmCount"]
        self.worldCitiesCount      = details["worldCitiesCount"]
        self.dstCount              = details["dstCount"]
        self.shortLightDuration    = details["shortLightDuration"]
        self.longLightDuration     = details["longLightDuration"]
        self.weekLanguageSupported = details["weekLanguageSupported"]
        self.worldCities           = details["worldCities"]
        self.temperature           = details["temperature"]
        self.batteryLevelLowerLimit= details["batteryLevelLowerLimit"]
        self.batteryLevelUpperLimit= details["batteryLevelUpperLimit"]
        self.alwaysConnected       = details["alwaysConnected"]
        self.findButtonUserDefined = details["findButtonUserDefined"]
        self.hasPowerSavingMode    = details["hasPowerSavingMode"]
        self.hasDnD                = details["hasDnD"]
        self.hasBatteryLevel       = details["hasBatteryLevel"]
        self.hasWorldCities        = details["hasWorldCities"]

    def lookup_watch_info(self, name):
        # Public non-destructive lookup
        return self._resolve_watch_details(name)

    def _resolve_watch_details(self, name):
        # Internal method for lookup logic
        shortName = None
        model = WATCH_MODEL.UNKNOWN

        parts = name.split(" ")
        if len(parts) > 1:
            shortName = parts[1]  # instead of `parts`
        if not shortName:
            return None  # Could return a dict of defaults or None

        if shortName in {"ECB-10", "ECB-20", "ECB-30"}:
            model = WATCH_MODEL.ECB
        elif shortName.startswith("ABL"):
            model = WATCH_MODEL.ABL
        elif shortName.startswith("GST"):
            model = WATCH_MODEL.GST
        else:
            prefix_map = [
                ("MSG", WATCH_MODEL.MSG),
                ("GPR", WATCH_MODEL.GPR),
                ("GM-B2100", WATCH_MODEL.GA),
                ("GBM", WATCH_MODEL.GA),
                ("GBD", WATCH_MODEL.GBD),
                ("GMW", WATCH_MODEL.GMW),
                ("DW-H",  WATCH_MODEL.DW_H),
                ("DW",  WATCH_MODEL.DW),
                ("GA",  WATCH_MODEL.GA),
                ("GB",  WATCH_MODEL.GB),
                ("GM",  WATCH_MODEL.GM),
                ("GW",  WATCH_MODEL.GW),
                ("MRG", WATCH_MODEL.MRG),
                ("ABL", WATCH_MODEL.ABL),
            ]
            for prefix, m in prefix_map:
                if shortName.startswith(prefix):
                    model = m
                    break

        model_info = self.model_map.get(model, {})
        computed = {
            "name": name,
            "shortName": shortName,
            "model": model,
            # Use model_info for each property
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
        return computed

    def set_address(self, address):
        self.address = address

    def get_address(self):
        return self.address

    def get_model(self):
        return self.model

    def reset(self):
        self.address = ""
        self.name = ""
        self.shortName = ""
        self.model = WATCH_MODEL.UNKNOWN

watch_info = WatchInfo()
