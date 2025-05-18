from enum import Enum

class NotificationType(Enum):
    EMAIL_SMS = 6
    CALENDAR = 5

class AppNotification:
    def __init__(self, type: NotificationType, timestamp: str, app: str, title: str, text: str):
        """
        Initializes a AppNotification object.
        """
        self.type = type
        self.timestamp = timestamp
        self.app = app
        self.title = title[:17] # Truncate title to 17 characters, otherwise cannot send
        self.text = text

    def to_dict(self) -> dict:
        """
        Converts the AppNotification object to a dictionary.

        Returns:
            dict: A dictionary representation of the AppNotification object.
        """
        return {
            "type": self.type,
            "timestamp": self.timestamp,
            "app": self.app,
            "title": self.title,
            "text": self.text,
        }
    
