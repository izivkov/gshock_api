from gshock_api.iolib.app_notification_io import AppNotificationIO

bufferSMS = "fdfffffffffef9cdcfcdcacfcaceccabcec7cfcdcdcef7ffb29a8c8c9e989a8cf1ffd7cbcec9d6dfc7ccccd2cdcfc8c7ffffe6ffab97968cdf968cdf9edf8c96928f939adf929a8c8c9e989adf"
bufferSMS_2 = "fcfffffffffef9cdcfcdcacfcaceccabcec7cfcdcac6f7ffb29a8c8c9e989a8cf1ffd7cbcec9d6dfc7ccccd2cdcfc8c7fffff4ffbe91908b979a8ddf90919a"
bufferGmail = "fffffffffffef9cdcfcdcacfcaceceabcfc8cbcccecffaffb8929e9693fdff929affff05ffab97968cdf968cdf9edf899a8d86df93909198df8c8a9d959a9c8bd1dfb29e86899adf9a899a91df8b9090df93909198d1dfbd8a8bdf979a8d9adf968bdf968cd1d1d1f5a8979e8bdf968cdf968bc0f5b6df8b97969194df889adf9c9e91df9b90df9d9a8b8b9a8ddf8b979e91df8b979adf909999969c969e93dfbc9e8c9690dfb8d2ac97909c94dfbe8f8fdedfab97968cdf9e8f8fdf8f8d9089969b9a8cdf8b979adf999093939088969198df9a878b8d9edf999a9e8b8a8d9a8cc5f5ac9a8b8cdf889e8b9c97d88cdf8d9a9296919b"
bufferGmailJapanese = "fefffffffffef9cdcfcdcacfcacec9abcdcececacdcffaffb8929e9693fdff929affff9aff1a42431a5a4c1c7e501c7c6b1c7d5df51a42431a5a4c1c7e501c7c6b1c7d5d1c7c711c7d6d1a43411c7e7b1c7e601c7d751c7f7e184a4a1c7d6d1970701c7e701c7e511c7e731a5a421c7e721c7e581c7e661c7f7d1c7c551c7d5d1a7a7a1c7e581c7e66f5"
bufferCalendar = "f7fffffffffefacdcfcdcacfcaceceabcdcdcecfcfcff7ffbc9e939a919b9e8debff1d7f711d7f55b0919ad28b96929a1d7f531d7f71ffffe1ff1d7f711d7f55cecfc5cbcfdf1d7f6cdfcecec5cbcfdfafb21d7f531d7f71"
bufferCalendar2 = "f9fffffffffefacdcfcdcacfcaceceabcdcdcfc6cfcbf7ffbc9e939a919b9e8ddaff1d7f711d7f55b290919b9e86dfba899a8d86df889a9a94df99908d9a899a8d1d7f531d7f71ffffe1ff1d7f711d7f55cecfc5cccfdf1d7f6cdfcecec5cccfdfafb21d7f531d7f71"
bufferAllDayEvent = "fdfffffffffefacdcfcdcacfcacec9abcdcccccfcfcff7ffbc9e939a919b9e8de3ff1d7f711d7f55b98a9393df9b9e86df9a899a918bdfcc1d7f531d7f71ffffebff1d7f711d7f55ab9092908d8d90881d7f531d7f71"  # noqa: N816


def format_hex_string(hexstr):
    """Format a hex string into space-separated bytes."""
    return " ".join(hexstr[i : i + 2] for i in range(0, len(hexstr), 2))


# Example usage
input_hex_2 = AppNotificationIO.xor_decode_buffer(bufferGmailJapanese).hex()
buf = bytes.fromhex(input_hex_2)


notification = AppNotificationIO.decode_notification_packet(buf)
print(notification)


rebuilt_buf = AppNotificationIO.encode_notification_packet(notification)


def compare_buffers(buf1: bytes, buf2: bytes):
    min_len = min(len(buf1), len(buf2))
    for i in range(min_len):
        if buf1[i] != buf2[i]:
            print(f"Difference at byte {i}:")
            print(f"  buf1: {buf1[i]:02x}")
            print(f"  buf2: {buf2[i]:02x}")
            print(f"  Context buf1: ... {buf1[max(0,i-5):i+5].hex()} ...")
            print(f"  Context buf2: ... {buf2[max(0,i-5):i+5].hex()} ...")
            break
    else:
        if len(buf1) != len(buf2):
            print(f"Buffers have different lengths: {len(buf1)} vs {len(buf2)}")
        else:
            print("No differences found.")


# Usage:
compare_buffers(rebuilt_buf, buf)
