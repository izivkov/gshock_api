from dataclasses import dataclass
from enum import Enum


class NotificationType(Enum):
    GENERIC = 0
    PHONE_CALL_URGENT = 1
    PHONE_CALL = 2
    EMAIL = 3
    MESSAGE = 4
    CALENDAR = 5
    EMAIL_SMS = 6


@dataclass
class AppNotification:
    type: NotificationType
    timestamp: str
    app: str
    title: str
    text: str
    short_text: str = ""

    def __post_init__(self) -> None:
        max_length_text: int = 193
        max_length_short_text: int = 40
        max_combined: int = 206

        text_bytes: bytes = self.text.encode("utf-8")
        if len(text_bytes) > max_length_text:
            self.text = text_bytes[:max_length_text].decode("utf-8", errors="ignore")

        short_text_bytes: bytes = self.short_text.encode("utf-8")
        if len(short_text_bytes) > max_length_short_text:
            self.short_text = short_text_bytes[:max_length_short_text].decode(
                "utf-8", errors="ignore"
            )

        text_bytes = self.text.encode("utf-8")
        short_text_bytes = self.short_text.encode("utf-8")
        total_len: int = len(text_bytes) + len(short_text_bytes)
        if total_len > max_combined:
            allowed_text_bytes: int = max(0, max_combined - len(short_text_bytes))
            self.text = text_bytes[:allowed_text_bytes].decode("utf-8", errors="ignore")

    def to_dict(self) -> dict[str, object]:
        return {
            "type": self.type,
            "timestamp": self.timestamp,
            "app": self.app,
            "title": self.title,
            "text": self.text,
            "short_text": self.short_text,
        }
