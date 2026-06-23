from importlib.metadata import PackageNotFoundError, version  # pragma: no cover

try:
    dist_name = "gshock_api"
    __version__ = version(dist_name)
except PackageNotFoundError:  # pragma: no cover
    __version__ = "unknown"
finally:
    del version, PackageNotFoundError

# Display version upon import
print(f"Loaded gshock_api version {__version__}")  # noqa: T201
