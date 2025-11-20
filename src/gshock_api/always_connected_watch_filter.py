import time
from typing import Any, Dict  # noqa: UP035

from gshock_api.watch_info import watch_info


class AlwaysConnectedWatchFilter:
    """
    For always-connected watches, limit the connection frequency to once every 6 hours.
    Otherwise, they may block other watches from connecting.
    """

    # self.last_connected_times maps watch names (str) to Unix timestamps (float)
    def __init__(self) -> None:
        self.last_connected_times: Dict[str, float] = {}

    def connection_filter(self, watch_name: str) -> bool:
        # Assuming lookup_watch_info returns a dict, possibly with more keys
        watch: dict[str, Any] = watch_info.lookup_watch_info(watch_name)

        if not watch["alwaysConnected"]:
            # not always connected - allow...
            return True

        # Use Optional[float] since .get() can return None
        last_time: float | None = self.last_connected_times.get(watch_name)
        now: float = time.time()

        if last_time is None:
            # connected for the first time - allow...
            self.update_connection_time(watch_name=watch_name)
            return True

        elapsed: float = now - last_time
        # 6 hours in seconds: 6 * 60 minutes/hour * 60 seconds/minute = 21600 seconds
        SIX_HOURS_IN_SECONDS: int = 6 * 3600  # noqa: N806
        
        if elapsed > SIX_HOURS_IN_SECONDS:
            # last connected more than 6 hours ago - allow...
            self.update_connection_time(watch_name=watch_name)
            return True

        # last connected less than 6 hours ago - deny...
        return False

    def update_connection_time(self, watch_name: str) -> None:
        self.last_connected_times[watch_name.strip()] = time.time()


always_connected_watch_filter: AlwaysConnectedWatchFilter = AlwaysConnectedWatchFilter()