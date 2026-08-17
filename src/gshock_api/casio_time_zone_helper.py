from dataclasses import dataclass
from datetime import datetime, timezone
from typing import NamedTuple
from zoneinfo import ZoneInfo


class LatLon(NamedTuple):
    lat: float
    lon: float


@dataclass
class CasioTimeZone:
    name: str
    zone_name: str
    dst_rules: int = 0

    @property
    def zone_id(self) -> ZoneInfo | timezone:
        try:
            return ZoneInfo(self.zone_name)
        except Exception:
            return timezone.utc

    def is_in_dst(self) -> bool:
        try:
            now = datetime.now(self.zone_id)
            return now.dst() is not None and now.dst().total_seconds() != 0
        except Exception:
            return False


class CasioTimeZoneHelper:
    """Helper class providing Casio timezone mapping and coordinates lookup."""

    TIME_ZONE_TABLE: list[CasioTimeZone] = [
        CasioTimeZone("BAKER ISLAND", "UTC-12"),
        CasioTimeZone("MARQUESAS ISLANDS", "Pacific/Marquesas", 0xDA),
        CasioTimeZone("POGO POGO", "Pacific/Pago_Pago"),
        CasioTimeZone("HONOLULU", "Pacific/Honolulu"),
        CasioTimeZone("ANCHORAGE", "America/Anchorage", 0x1),
        CasioTimeZone("LOS ANGELES", "America/Los_Angeles", 0x1),
        CasioTimeZone("DENVER", "America/Denver", 0x1),
        CasioTimeZone("CHICAGO", "America/Chicago", 0x1),
        CasioTimeZone("NEW YORK", "America/New_York", 0x1),
        CasioTimeZone("HALIFAX", "America/Halifax", 0x1),
        CasioTimeZone("ST.JOHN'S", "America/St_Johns", 0x1),
        CasioTimeZone("RIO DE JANEIRO", "America/Sao_Paulo"),
        CasioTimeZone("F.DE NORONHA", "America/Noronha"),
        CasioTimeZone("PRAIA", "Atlantic/Cape_Verde"),
        CasioTimeZone("UTC", "UTC"),
        CasioTimeZone("LONDON", "Europe/London", 0x02),
        CasioTimeZone("PARIS", "Europe/Paris", 0x02),
        CasioTimeZone("ATHENS", "Europe/Athens", 0x02),
        CasioTimeZone("JEDDAH", "Asia/Riyadh", 0x0),
        CasioTimeZone("JERUSALEM", "Asia/Jerusalem", 0x2A),
        CasioTimeZone("TEHRAN", "Asia/Tehran", 0x2B),
        CasioTimeZone("DUBAI", "Asia/Dubai"),
        CasioTimeZone("KABUL", "Asia/Kabul"),
        CasioTimeZone("KARACHI", "Asia/Karachi"),
        CasioTimeZone("DELHI", "Asia/Kolkata"),
        CasioTimeZone("KATHMANDU", "Asia/Kathmandu"),
        CasioTimeZone("DHAKA", "Asia/Dhaka"),
        CasioTimeZone("YANGON", "Asia/Yangon"),
        CasioTimeZone("BANGKOK", "Asia/Bangkok"),
        CasioTimeZone("HONG KONG", "Asia/Hong_Kong"),
        CasioTimeZone("PYONGYANG", "Asia/Pyongyang"),
        CasioTimeZone("EUCLA", "Australia/Eucla"),
        CasioTimeZone("TOKYO", "Asia/Tokyo"),
        CasioTimeZone("ADELAIDE", "Australia/Adelaide", 0x4),
        CasioTimeZone("SYDNEY", "Australia/Sydney", 0x4),
        CasioTimeZone("LORD HOWE ISLAND", "Australia/Lord_Howe", 0x12),
        CasioTimeZone("NOUMEA", "Pacific/Noumea"),
        CasioTimeZone("WELLINGTON", "Pacific/Auckland", 0x5),
        CasioTimeZone("CHATHAM ISLANDS", "Pacific/Chatham", 0x17),
        CasioTimeZone("NUKUALOFA", "Pacific/Tongatapu"),
        CasioTimeZone("KIRITIMATI", "Pacific/Kiritimati"),
        CasioTimeZone("CASABLANCA", "Africa/Casablanca", 0x0F),
        CasioTimeZone("BEIRUT", "Asia/Beirut", 0x0C),
        CasioTimeZone("NORFOLK ISLAND", "Pacific/Norfolk", 0x04),
        CasioTimeZone("EASTER ISLAND", "Pacific/Easter", 0x1C),
        CasioTimeZone("HAVANA", "America/Havana", 0x15),
        CasioTimeZone("SANTIAGO", "America/Santiago", 0x1B),
        CasioTimeZone("ASUNCION", "America/Asuncion", 0x09),
        CasioTimeZone("PONTA DELGADA", "Atlantic/Azores", 0x02),
    ]

    TIME_ZONE_MAP: dict[str, CasioTimeZone] = {tz.zone_name: tz for tz in TIME_ZONE_TABLE}

    WORLD_CITY_COORDINATES: dict[str, LatLon] = {
        "Asia/Ho_Chi_Minh": LatLon(10.7958, 106.7062),
        "Europe/Madrid": LatLon(41.4548, 2.2502),
        "Asia/Shanghai": LatLon(22.7230, 114.2611),
        "UTC-12": LatLon(0.1936, -176.4769),
        "Pacific/Marquesas": LatLon(-8.9167, -140.1000),
        "Pacific/Pago_Pago": LatLon(-14.2781, -170.7025),
        "Pacific/Honolulu": LatLon(21.3069, -157.8583),
        "America/Anchorage": LatLon(61.2181, -149.9003),
        "America/Los_Angeles": LatLon(34.0522, -118.2437),
        "America/Denver": LatLon(39.7392, -104.9903),
        "America/Chicago": LatLon(41.8781, -87.6298),
        "America/New_York": LatLon(40.7128, -74.0060),
        "America/Halifax": LatLon(44.6488, -63.5752),
        "America/St_Johns": LatLon(47.5615, -52.7126),
        "America/Sao_Paulo": LatLon(-22.9068, -43.1729),
        "America/Noronha": LatLon(-3.8536, -32.4297),
        "Atlantic/Cape_Verde": LatLon(14.9330, -23.5133),
        "UTC": LatLon(0.0, 0.0),
        "Europe/London": LatLon(51.5074, -0.1278),
        "Europe/Paris": LatLon(48.8566, 2.3522),
        "Europe/Athens": LatLon(37.9838, 23.7275),
        "Asia/Riyadh": LatLon(21.4858, 39.1925),
        "Asia/Jerusalem": LatLon(31.7683, 35.2137),
        "Asia/Tehran": LatLon(35.6892, 51.3890),
        "Asia/Dubai": LatLon(25.2048, 55.2708),
        "Asia/Kabul": LatLon(34.5553, 69.2075),
        "Asia/Karachi": LatLon(24.8607, 67.0011),
        "Asia/Kolkata": LatLon(28.6139, 77.2090),
        "Asia/Kathmandu": LatLon(27.7172, 85.3240),
        "Asia/Dhaka": LatLon(23.8103, 90.4125),
        "Asia/Yangon": LatLon(16.8661, 96.1951),
        "Asia/Bangkok": LatLon(13.7563, 100.5018),
        "Asia/Hong_Kong": LatLon(22.3193, 114.1694),
        "Asia/Pyongyang": LatLon(39.0392, 125.7625),
        "Australia/Eucla": LatLon(-31.6784, 128.8869),
        "Asia/Tokyo": LatLon(35.6762, 139.6503),
        "Australia/Adelaide": LatLon(-34.9285, 138.6007),
        "Australia/Sydney": LatLon(-33.8688, 151.2093),
        "Australia/Lord_Howe": LatLon(-31.5553, 159.0821),
        "Pacific/Noumea": LatLon(-22.2758, 166.4581),
        "Pacific/Auckland": LatLon(-41.2865, 174.7762),
        "Pacific/Chatham": LatLon(-43.9500, -176.5500),
        "Pacific/Tongatapu": LatLon(-21.1789, -175.1982),
        "Pacific/Kiritimati": LatLon(1.8721, -157.4278),
        "Africa/Casablanca": LatLon(33.5731, -7.5898),
        "Asia/Beirut": LatLon(33.8938, 35.5018),
        "Pacific/Norfolk": LatLon(-29.0408, 167.9547),
        "Pacific/Easter": LatLon(-27.1127, -109.3497),
        "America/Havana": LatLon(23.1136, -82.3666),
        "America/Santiago": LatLon(-33.4489, -70.6693),
        "America/Asuncion": LatLon(-25.2637, -57.5759),
        "Atlantic/Azores": LatLon(37.7412, -25.6756),
    }

    @classmethod
    def get_local_casio_time_zone(cls) -> CasioTimeZone:
        """Determines the local system CasioTimeZone."""
        try:
            local_tz = datetime.now().astimezone().tzinfo
            if hasattr(local_tz, "key"):
                tz_key = local_tz.key
                if tz_key in cls.TIME_ZONE_MAP:
                    return cls.TIME_ZONE_MAP[tz_key]
        except Exception:
            pass
        return cls.TIME_ZONE_MAP.get("UTC", CasioTimeZone("UTC", "UTC"))

    @classmethod
    def find_time_zone(cls, time_zone_name: str) -> CasioTimeZone:
        if time_zone_name in cls.TIME_ZONE_MAP:
            return cls.TIME_ZONE_MAP[time_zone_name]
        for tz in cls.TIME_ZONE_TABLE:
            if tz.name == time_zone_name.upper():
                return tz
        name = time_zone_name.split("/")[-1].upper()
        return CasioTimeZone(name, time_zone_name, 0x00)

    @classmethod
    def get_world_city_coordinates(cls, zone_id: str) -> tuple[float, float, bool]:
        """Returns (lat, lon, is_exact) for the given timezone string."""
        if zone_id in cls.WORLD_CITY_COORDINATES:
            coords = cls.WORLD_CITY_COORDINATES[zone_id]
            return coords.lat, coords.lon, True

        # Fallback estimation based on UTC offset
        try:
            tz = ZoneInfo(zone_id)
            now = datetime.now(tz)
            offset_hours = now.utcoffset().total_seconds() / 3600.0 if now.utcoffset() else 0.0
            approx_lon = max(min(offset_hours * 15.0, 180.0), -180.0)
            return 0.0, approx_lon, False
        except Exception:
            return 0.0, 0.0, False
