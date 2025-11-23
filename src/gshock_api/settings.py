from dataclasses import dataclass


@dataclass
class Settings:
    """Settings for G-Shock watch configuration"""
    # Instance attributes with default values and type hints
    time_format: str = ""
    date_format: str = ""
    language: str = ""
    auto_light: bool = False
    light_duration: str = ""
    power_saving_mode: bool = False
    button_tone: bool = True
    time_adjustment: bool = True

# Instantiate the settings object using the typed dataclass
settings: Settings = Settings()