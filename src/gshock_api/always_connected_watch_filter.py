import time

from gshock_api.watch_info import watch_info


class AlwaysConnectedWatchFilter:
    """
    For always-connected watches, limit the connection frequency to once every 6 hours.
    Otherwise, they may block other watches from connecting.
    """

    def __init__(self) -> None:
        self.last_connected_times: dict[str, float] = {}

    def connection_filter(self, watch_name: str) -> bool:
        # Assuming lookup_watch_info returns a dict with string keys and any values
        watch: dict[str, object] = watch_info.lookup_watch_info(watch_name)

        if not watch or not watch.get("alwaysConnected", False):
            # not always connected - allow...
            return True

        last_time: float | None = self.last_connected_times.get(watch_name)
        now: float = time.time()

        if last_time is None:
            # connected for the first time - allow...
            self.update_connection_time(watch_name=watch_name)
            return True

        elapsed: float = now - last_time
        SIX_HOURS_IN_SECONDS: int = 6 * 3600  # 21600 seconds

        if elapsed > SIX_HOURS_IN_SECONDS:
            # last connected more than 6 hours ago - allow...
            self.update_connection_time(watch_name=watch_name)
            return True

        # last connected less than 6 hours ago - deny...
        return False

    def update_connection_time(self, watch_name: str) -> None:
        self.last_connected_times[watch_name.strip()] = time.time()


always_connected_watch_filter = AlwaysConnectedWatchFilter()
