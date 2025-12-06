"""Singleton app settings"""

from typing import Any

from PySide6.QtCore import QSettings


class AppConfig:
    """Singleton app settings."""
    _settings: QSettings = QSettings("FOSFC", "free-fan-control")

    @classmethod
    def get(cls, key: str, default: Any=None, value_type: type=str) -> Any:
        """Get value from settings."""
        return cls._settings.value(key, default, type=value_type)

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        """Set value in settings."""
        cls._settings.setValue(key, value)
