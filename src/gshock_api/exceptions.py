# gshock_api/exceptions.py
from __future__ import annotations  # For cleaner forward references if needed later


class GShockError(Exception):
    """Base exception for all G-Shock errors."""
    pass

class GShockConnectionError(GShockError):
    """Raised when BLE connection to G-Shock device fails."""    
    pass

class GShockIgnorableException(GShockConnectionError):  # noqa: N818
    """Raised when BLE connection to G-Shock device fails."""    
    pass