from gshock_api.app_notification import AppNotification, NotificationType

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

    def read_length_prefixed_string(buf: bytes, offset: int) -> tuple[str, int]:
        if offset + 2 > len(buf):
            raise ValueError("Not enough data to read length prefix")

        length = buf[offset]
        if buf[offset + 1] != 0x00:
            raise ValueError("Expected null second byte in length prefix")

        start = offset + 2
        end = start + length
        if end > len(buf):
            raise ValueError("String length exceeds buffer")

        string = buf[start:end].decode("utf-8")
        return string, end

    def decode_notification_packet(buf: bytes) -> AppNotification:
        """
        Decodes a G-Shock calendar notification buffer into an AppNotification object.
        """
        offset = 0

        if len(buf) < 6:
            raise ValueError("Buffer too short")

        # Read 6-byte header (skip or store if needed)
        offset = 6

        # Read 1-byte type
        notif_type = buf[offset]
        notif_type_enum = NotificationType(notif_type)
        offset += 1

        # Read 15-byte ASCII timestamp
        timestamp_raw = buf[offset:offset + 15].decode("ascii")
        offset += 15

        # Read app name (length-prefixed UTF-8 string)
        app, offset = AppNotificationIO.read_length_prefixed_string(buf, offset)

        # Read title (length-prefixed UTF-8 string)
        title, offset = AppNotificationIO.read_length_prefixed_string(buf, offset)

        # Read empty string (length-prefixed UTF-8 string, skip)
        _, offset = AppNotificationIO.read_length_prefixed_string(buf, offset)

        # Read text (length-prefixed UTF-8 string)
        text, offset = AppNotificationIO.read_length_prefixed_string(buf, offset)

        # Construct and return AppNotification object
        notification = AppNotification(
            type = notif_type_enum,
            timestamp=timestamp_raw,
            app=app,
            title=title,
            text=text
        )
        return notification
        
    
    def write_length_prefixed_string(text: str) -> bytes:
        encoded = text.encode("utf-8")
        if len(encoded) > 255:
            raise ValueError("Encoded string too long")
        return bytes([len(encoded), 0x00]) + encoded

    def encode_notification_packet(data: AppNotification) -> bytes:
        """
        Encodes a dictionary representing a G-Shock notification into a binary buffer.
        """

        if not isinstance(data, AppNotification):
            raise TypeError("data must be an AppNotification instance")
    
        header = "010000000001"
        result = bytearray()
        result += bytes.fromhex(header)
        result.append(data.type.value)
        result += data.timestamp.encode("ascii")
        result += AppNotificationIO.write_length_prefixed_string(data.app)
        result += AppNotificationIO.write_length_prefixed_string(data.title)
        result += AppNotificationIO.write_length_prefixed_string("")  # Empty string for the separator
        result += AppNotificationIO.write_length_prefixed_string(data.text)
        return bytes(result)
