from enum import Enum

class NotificationType(Enum):
    EMAIL_SMS = 6
    CALENDAR = 5

class CalendarNotification:
    def __init__(self, date_time: str, source_app: str, title: str, start_time: str, end_time: str):
        """
        Initializes a CalendarNotification object.

        Args:
            date_time (str): The date and time of the notification in the format YYYYMMDDTHHMMSS.
            source_app (str): The source application of the notification.
            title (str): The title of the calendar event.
            start_time (str): The start time of the event.
            end_time (str): The end time of the event.
        """
        self.type = NotificationType.CALENDAR.value
        self.date_time = date_time
        self.source_app = source_app
        self.title = title[:17] # Truncate title to 17 characters, otherwise cannot send
        self.start_time = start_time
        self.end_time = end_time

    def to_dict(self) -> dict:
        """
        Converts the CalendarNotification object to a dictionary.

        Returns:
            dict: A dictionary representation of the CalendarNotification object.
        """
        return {
            "type": self.type,
            "date_time": self.date_time,
            "source_app": self.source_app,
            "title": self.title,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }
    
class EmailSmsNotification:
    def __init__(self, date_time: str, source_app: str, sender: str, message: str):
        """
        Initializes an EmailSmsNotification object.

        Args:
            date_time (str): The date and time of the notification in the format YYYYMMDDTHHMMSS.
            source_app (str): The source application of the notification.
            sender (str): The sender of the email or SMS.
            message (str): The content of the email or SMS.
        """
        self.notification_type = NotificationType.EMAIL_SMS.value
        self.date_time = date_time
        self.source_app = source_app
        self.sender = sender
        self.message = message

    def to_dict(self) -> dict:
        """
        Converts the EmailSmsNotification object to a dictionary.

        Returns:
            dict: A dictionary representation of the EmailSmsNotification object.
        """
        return {
            "notification_type": self.notification_type,
            "date_time": self.date_time,
            "source_app": self.source_app,
            "sender": self.sender,
            "message": self.message,
        }
    
