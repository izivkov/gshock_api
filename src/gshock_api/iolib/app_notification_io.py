from datetime import datetime
from gshock_api.app_notification import EmailSmsNotification, CalendarNotification

class AppNotificationIO:
    def xor_decode_buffer(buffer: str, key: int = 255) -> bytes:
        """
        Decodes a hex-encoded buffer using XOR with the given key.

        Args:
            buffer (str): The hex-encoded buffer as a string.
            key (int): The XOR key to decode the buffer.

        Returns:
            bytes: The XOR-decoded bytes.
        """
        buffer_bytes = bytes.fromhex(buffer)
        decoded_bytes = bytes(b ^ key for b in buffer_bytes)
        return decoded_bytes

    def xor_encode_buffer(decoded_bytes: bytes, key: int = 255) -> str:
        """
        Encodes a buffer using XOR with the given key.

        Args:
            decoded_bytes (bytes): The original decoded bytes to encode.
            key (int): The XOR key to encode the buffer.

        Returns:
            str: The XOR-encoded buffer as a hex string.
        """
        encoded_bytes = bytes(b ^ key for b in decoded_bytes)
        return encoded_bytes.hex()

    def create_buffer_from_email_sms(email_sms: EmailSmsNotification) -> bytes:
        """
        Creates an SMS buffer from an EmailSmsNotification object.

        Args:
            email_sms (EmailSmsNotification): The EmailSmsNotification object.

        Returns:
            bytes: The reconstructed SMS buffer as bytes.
        """
        # Step 1: Header
        header = bytes.fromhex("00000000000106")

        # Step 2: Date-Time
        date_time = email_sms.date_time.encode("utf-8")

        # Step 3: Source App
        source_app = email_sms.source_app
        source_length = len(source_app)
        source_bytes = source_length.to_bytes(1, "big") + b"\x00" + source_app.encode("utf-8")

        # Step 4: Sender Phone Number
        sender = email_sms.sender
        sender_length = len(sender)
        sender_bytes = sender_length.to_bytes(1, "big") + b"\x00" + sender.encode("utf-8")

        # Step 5: Message
        message = email_sms.message
        message_length = len(message)
        message_bytes = message_length.to_bytes(1, "big") + b"\x00" + message.encode("utf-8")

        # Combine all parts
        buffer = header + date_time + source_bytes + sender_bytes + b"\x00\x00" + message_bytes

        return buffer

    def create_buffer_from_calendar(calendar: CalendarNotification) -> bytes:
        """
        Creates a decoded buffer from a CalendarNotification object.

        Args:
            calendar (CalendarNotification): The CalendarNotification object.

        Returns:
            bytes: The decoded buffer as bytes.
        """
        # Step 1: Fixed header
        header = bytes.fromhex("00000000000105")

        # Step 2: Date-time
        date_time_bytes = calendar.date_time.encode("utf-8")

        # Step 3: Source
        source = calendar.source_app
        source_length = len(source)
        source_bytes = source_length.to_bytes(1, "big") + b"\x00" + source.encode("utf-8")

        # Step 4: Title
        title = calendar.title
        title_separator = b"\x1d\x00\xe2\x80\x8e\xe2\x80\xaa"  # Separator before the title
        title_bytes = title_separator + title.encode("utf-8")

        # Step 5: Start time and end time
        start_time = calendar.start_time
        end_time = calendar.end_time
        time_separator = b"\xe2\x80\xac\xe2\x80\x8e\x00\x00\x1e\x00\xe2\x80\x8e\xe2\x80\xaa"  # Separator before times
        start_time_bytes = start_time.encode("utf-8")
        end_time_separator = b"\xe2\x80\x93"  # Separator between start and end times
        end_time_bytes = end_time.encode("utf-8")

        # Add the missing sequence after "280aa31303a3430"
        additional_sequence = b"\x20\xe2\x80\x93\x20" + end_time_bytes + b"\xe2\x80\xac\xe2\x80\x8e"

        # Combine start and end times
        time_bytes = time_separator + start_time_bytes + additional_sequence

        # Step 6: Combine all parts
        decoded_buffer = header + date_time_bytes + source_bytes + title_bytes + time_bytes

        return decoded_buffer

    @staticmethod
    def get_encoded_buffer(notification) -> str:
        """
        Encodes a buffer based on the notification type (calendar or email/SMS).

        Args:
            notification: The notification object (either EmailSmsNotification or CalendarNotification).

        Returns:
            str: The XOR-encoded buffer as a hex string.

        Raises:
            ValueError: If the notification type is not supported.
        """
        if isinstance(notification, EmailSmsNotification):
            # Handle email/SMS notification
            buffer = AppNotificationIO.create_buffer_from_email_sms(notification)
        elif isinstance(notification, CalendarNotification):
            # Handle calendar notification
            buffer = AppNotificationIO.create_buffer_from_calendar(notification)
        else:
            # Raise an error for unsupported types
            raise ValueError(f"Unsupported notification type: {type(notification)}")

        # Encode the buffer using XOR
        return AppNotificationIO.xor_encode_buffer(buffer)


# Example usage
if __name__ == "__main__":
    calendar_notification = CalendarNotification(
        date_time="20231001T120000",
        source_app="CalendarApp",
        title="Meeting with Team",
        start_time="10:15 ",
        end_time="11:40 PM"
    )

    email_notification = EmailSmsNotification(
        date_time="20231001T120000",
        source_app="EmailApp",
        sender="Ivo",
        message="Hello, this is a test message."
    )

    encoded = AppNotificationIO.get_encoded_buffer(calendar_notification)
    print(f"Encoded Calendar Notification: {encoded}")

    encoded = AppNotificationIO.get_encoded_buffer(email_notification)
    print(f"Encoded Email Notification: {encoded}")