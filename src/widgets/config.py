"""Singleton app settings"""

from typing import Any

from PyQt6.QtCore import QSettings

class AppConfig:
    """Singleton app settings."""
    _settings: QSettings = QSettings("self", "nzxt-fan-control")

    @classmethod
    def get(cls, key: str, default: Any=None) -> Any:
        """Get value from settings."""
        value_type: type = str
        if key in ["start_minimized", "minimize_on_exit"]:
            value_type = bool
        return cls._settings.value(key, default, type=value_type)

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        """Set value in settings."""
        cls._settings.setValue(key, value)
