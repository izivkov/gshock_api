from enum import Enum
from dataclasses import dataclass

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
    text2: str = ""

    def __post_init__(self):
        max_length_text = 193
        max_length_text2 = 40
        max_combined = 200  # Example combined max in bytes

        # Truncate individual fields by UTF-8 byte length
        text_bytes = self.text.encode("utf-8")
        if len(text_bytes) > max_length_text:
            # Truncate to max_length_text bytes, decode safely
            self.text = text_bytes[:max_length_text].decode("utf-8", errors="ignore")

        text2_bytes = self.text2.encode("utf-8")
        if len(text2_bytes) > max_length_text2:
            self.text2 = text2_bytes[:max_length_text2].decode("utf-8", errors="ignore")

        # Now check combined UTF-8 byte length
        text_bytes = self.text.encode("utf-8")
        text2_bytes = self.text2.encode("utf-8")
        total_len = len(text_bytes) + len(text2_bytes)
        if total_len > max_combined:
            # Calculate how much to trim
            excess = total_len - max_combined
            # Split excess as evenly as possible
            trim_text = min(len(text_bytes), excess // 2 + excess % 2)
            trim_text2 = min(len(text2_bytes), excess // 2)
            self.text = text_bytes[:len(text_bytes) - trim_text].decode("utf-8", errors="ignore") if trim_text > 0 else self.text
            self.text2 = text2_bytes[:len(text2_bytes) - trim_text2].decode("utf-8", errors="ignore") if trim_text2 > 0 else self.text2

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "timestamp": self.timestamp,
            "app": self.app,
            "title": self.title,
            "text": self.text,
            "text2": self.text2,
        }
    
