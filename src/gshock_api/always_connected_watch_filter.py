import time
from gshock_api.watch_info import watch_info

class AlwaysConnectedWatchFilter:
    """
    For always-connected watches, limit the connection frequency to once every 6 hours. 
    Otherwise, they may block other watches from connecting.
    """

    def __init__(self):
        self.last_connected_times = {}

    def connection_filter(self, watch_name):
        watch = watch_info.lookup_watch_info(watch_name)

        if not watch["alwaysConnected"]:
            # not always connected - allow...
            return True

        last_time = self.last_connected_times.get(watch_name)
        now = time.time()

        if last_time is None:
            # connected for the first time - allow...
            self.update_connection_time(watch_name=watch_name)
            return True

        elapsed = now - last_time
        if elapsed > 6 * 3600:
            # last connected more than 6 hours ago - allow...
            self.update_connection_time(watch_name=watch_name)
            return True

        # last connected less than 6 hours ago - deny...
        return False

    def update_connection_time(self, watch_name):
        self.last_connected_times[watch_name.strip()] = time.time()

always_connected_watch_filter = AlwaysConnectedWatchFilter()