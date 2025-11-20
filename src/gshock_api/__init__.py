from importlib.metadata import PackageNotFoundError, version  # pragma: no cover
import sys

try:
    dist_name = "gshock_api"
    __version__ = version(dist_name)
except PackageNotFoundError:  # pragma: no cover
    __version__ = "unknown"
finally:
    del version, PackageNotFoundError