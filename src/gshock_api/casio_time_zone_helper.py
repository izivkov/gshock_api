from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import NamedTuple
from zoneinfo import ZoneInfo


class LatLon(NamedTuple):
    lat: float
    lon: float


@dataclass
class CasioTimeZone:
    name: str
    zone_name: str
    _dst_rules: int = 0

    @property
    def zone_id(self) -> ZoneInfo:
        try:
            return ZoneInfo(self.zone_name)
        except Exception:
            return ZoneInfo("UTC")

    @property
    def offset(self) -> int:
        """Standard offset in 15-minute intervals."""
        try:
            now = datetime.now(self.zone_id)
            # Standard offset = Total offset - DST offset
            total_offset_seconds = now.utcoffset().total_seconds() if now.utcoffset() else 0
            dst_offset_seconds = now.dst().total_seconds() if now.dst() else 0
            return int((total_offset_seconds - dst_offset_seconds) / 60 / 15)
        except Exception:
            return 0

    @property
    def dst_offset(self) -> int:
        """DST offset in 15-minute intervals."""
        return int(self.get_dst_duration().total_seconds() / 60 / 15)

    @property
    def dst_rules(self) -> int:
        # If we have no DST for this timezone, override the dstRules with a 0
        return self._dst_rules if self.dst_offset > 0 else 0

    def is_in_dst(self) -> bool:
        try:
            now = datetime.now(self.zone_id)
            return now.dst() is not None and now.dst().total_seconds() != 0
        except Exception:
            return False

    def has_rules(self) -> bool:
        return self.dst_rules != 0

    def get_dst_duration(self) -> timedelta:
        """
        Calculates the daylight saving time (DST) offset duration.
        Matches Kotlin's getDTSDuration logic.
        """
        try:
            now = datetime.now(self.zone_id)
            # In Python, we can't easily get the 'next transition' like in Java's TimeZone API
            # without external libs like pytz, but we can check if it EVER has DST.
            # However, to be precise and match Kotlin:
            dst = now.dst()
            if dst and dst.total_seconds() != 0:
                return dst

            # If not currently in DST, we need to find if it has rules.
            # We can check a few months ahead/behind.
            # Summer in Northern Hemisphere (June)
            summer = datetime(now.year, 6, 21, tzinfo=self.zone_id)
            # Winter in Northern Hemisphere (Dec)
            winter = datetime(now.year, 12, 21, tzinfo=self.zone_id)

            dst_summer = summer.dst().total_seconds() if summer.dst() else 0
            dst_winter = winter.dst().total_seconds() if winter.dst() else 0

            max_dst = max(abs(dst_summer), abs(dst_winter))
            return timedelta(seconds=max_dst)

        except Exception:
            return timedelta(0)


class CasioTimeZoneHelper:
    """Helper class providing Casio timezone mapping and coordinates lookup."""

    _current_timezone: str = datetime.now().astimezone().tzname() or "UTC"
    _casio_timezone: CasioTimeZone | None = None

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

    @classmethod
    def set_timezone(cls, timezone_name: str | None) -> None:
        if timezone_name is None:
            from tzlocal import get_localzone_name
            timezone_name = get_localzone_name()

        cls._current_timezone = timezone_name
        cls._casio_timezone = cls.find_time_zone(timezone_name)

    @classmethod
    def get_casio_time_zone(cls) -> CasioTimeZone:
        if cls._casio_timezone is None:
            cls._casio_timezone = cls.find_time_zone(cls._current_timezone)
        return cls._casio_timezone

    @classmethod
    def is_equivalent(cls, tz1_name: str, tz2_name: str) -> bool:
        try:
            tz1 = ZoneInfo(tz1_name)
            tz2 = ZoneInfo(tz2_name)
            now = datetime.now()

            # Compare offsets and DST rules at current time and 6 months from now
            future = now + timedelta(days=182)

            for t in [now, future]:
                if tz1.utcoffset(t) != tz2.utcoffset(t):
                    return False
                if tz1.dst(t) != tz2.dst(t):
                    return False
            return True
        except Exception:
            return False

    @classmethod
    def find_time_zone(cls, time_zone_name: str) -> CasioTimeZone:
        if time_zone_name in cls.TIME_ZONE_MAP:
            return cls.TIME_ZONE_MAP[time_zone_name]

        for entry in cls.TIME_ZONE_TABLE:
            if cls.is_equivalent(entry.zone_name, time_zone_name):
                return entry

        # Fallback
        name = time_zone_name.split("/")[-1].replace("_", " ").upper()
        return CasioTimeZone(name, time_zone_name, 0x00)

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
    def find_time_zone_legacy(cls, time_zone_name: str) -> CasioTimeZone:
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
