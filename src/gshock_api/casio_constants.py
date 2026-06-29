from typing import Final


class CasioConstants:
    """
    Holds constants for Casio watch Bluetooth Low Energy (BLE) characteristics.
    Updated with handles and UUIDs for the GW-BX5600 model.
    """
    
    # BLE Characteristic UUIDs (str)
    CASIO_GET_DEVICE_NAME: Final[str] = "00002a00-0000-1000-8000-00805f9b34fb"
    CASIO_APPEARANCE: Final[str] = "00002a01-0000-1000-8000-00805f9b34fb"
    TX_POWER_LEVEL_CHARACTERISTIC_UUID: Final[str] = "00002a07-0000-1000-8000-00805f9b34fb"
    CASIO_READ_REQUEST_FOR_ALL_FEATURES_CHARACTERISTIC_UUID: Final[str] = (
        "26eb002c-b012-49a8-b1f8-394fb2032b0f"
    )
    CASIO_ALL_FEATURES_CHARACTERISTIC_UUID: Final[str] = "26eb002d-b012-49a8-b1f8-394fb2032b0f"
    CASIO_NOTIFICATION_CHARACTERISTIC_UUID: Final[str] = "26eb0030-b012-49a8-b1f8-394fb2032b0f"
    CASIO_DATA_REQUEST_SP_CHARACTERISTIC_UUID: Final[str] = "26eb0023-b012-49a8-b1f8-394fb2032b0f"
    CASIO_CONVOY_CHARACTERISTIC_UUID: Final[str] = "26eb0024-b012-49a8-b1f8-394fb2032b0f"
    SERIAL_NUMBER_STRING: Final[str] = "00002a25-0000-1000-8000-00805f9b34fb"

    # New UUIDs for Configuration (Handles 0x17 and 0x19)
    CASIO_SET_CONFIGURATION_CHARACTERISTIC_UUID: Final[str] = "26eb002e-b012-49a8-b1f8-394fb2032b0f"
    CASIO_GET_CONFIGURATION_CHARACTERISTIC_UUID: Final[str] = "26eb002f-b012-49a8-b1f8-394fb2032b0f"

    # Static Handle Constants (Replacing literals 0x07, 0x0E, 0x17, 0x19, etc.)
    HANDLE_DEVICE_NAME_LEGACY: Final[int] = 0x04
    HANDLE_APPEARANCE: Final[int] = 0x06
    HANDLE_DEVICE_NAME_GW: Final[int] = 0x07
    HANDLE_TX_POWER: Final[int] = 0x09
    HANDLE_READ_ALL_FEATURES: Final[int] = 0x0C
    HANDLE_ALL_FEATURES_NOTIFICATION: Final[int] = 0x0D
    HANDLE_ALL_FEATURES_WRITE: Final[int] = 0x0E
    HANDLE_CONFIG_WRITE: Final[int] = 0x17
    HANDLE_CONFIG_NOTIFY: Final[int] = 0x19
    HANDLE_SERIAL_NUMBER: Final[int] = 0xFF

    # Dictionary of Characteristic Names (str) mapped to their Command/Feature Codes (int)
    CHARACTERISTICS: Final[dict[str, int]] = {
        "CASIO_WATCH_NAME": 0x23,
        "CASIO_APP_INFORMATION": 0x22,
        "CASIO_BLE_FEATURES": 0x10,
        "CASIO_SETTING_FOR_BLE": 0x11,
        "CASIO_ADVERTISE_PARAMETER_MANAGER": 0x3B,
        "CASIO_CONNECTION_PARAMETER_MANAGER": 0x3A,
        "CASIO_MODULE_ID": 0x26,
        "CASIO_WATCH_CONDITION": 0x28,  # battery %
        "CASIO_VERSION_INFORMATION": 0x20,
        "CASIO_DST_WATCH_STATE": 0x1D,
        "CASIO_DST_SETTING": 0x1E,
        "CASIO_SERVICE_DISCOVERY_MANAGER": 0x47,
        "CASIO_CURRENT_TIME": 0x09,
        "CASIO_SETTING_FOR_USER_PROFILE": 0x45,
        "CASIO_SETTING_FOR_TARGET_VALUE": 0x43,
        "ALERT_LEVEL": 0x0A,
        "CASIO_SETTING_FOR_ALM": 0x15,
        "CASIO_SETTING_FOR_ALM2": 0x16,
        "CASIO_SETTING_FOR_BASIC": 0x13,
        "CASIO_CURRENT_TIME_MANAGER": 0x39,
        "CASIO_WORLD_CITIES": 0x1F,
        "CASIO_REMINDER_TITLE": 0x30,
        "CASIO_REMINDER_TIME": 0x31,
        "CASIO_TIMER": 0x18,
        "ERROR": 0xFF,
        "UNKNOWN": 0x0A,

        #  ECB-30 / GW-BX5600 specifics
        "CMD_SET_TIMEMODE": 0x47,
        "FIND_PHONE": 0x0A,

        # GW-BX5600 SP_DATA notification header bytes
        "GW_BX5600_SP_DATA_HEADER_03": 0x03,
        "GW_BX5600_SP_DATA_HEADER_05": 0x05,
        "GW_BX5600_SP_DATA_HEADER_06": 0x06,

        # HomeTime (dual time zone) characteristic
        "CASIO_HOME_TIME": 0x24,
    }