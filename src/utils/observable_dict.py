"""Custom observable dictionary."""

from typing import Any

from PySide6.QtCore import QObject, Signal


class ObservableDict(QObject):
    """Custom Dict with onChange signal."""

    value_changed: Signal = Signal(dict)

    def __init__(self, initial: dict|None=None):
        """INIT."""
        super().__init__()
        self.__data: dict[str, Any] = initial or {}

    def __getitem__(self, key: str) -> Any:
        """Get item from dict."""
        return self.__data.get(key, None)

    def __setitem__(self, key: str, value: Any) -> None:
        """Set value under given key in dict."""
        self.update(key, value)

    def __contains__(self, key: str) -> bool:
        """Check if given key exists in dict."""
        return key in self.__data

    def __repr__(self) -> str:
        """Print dict representation."""
        return repr(self.__data)

    def update(self, key: str, value: Any) -> None:
        """Update dict value under given key."""
        self.__data[key] = value
        self.value_changed.emit(self.__data.copy())

    def get_data(self) -> dict[str, Any]:
        """Get whole dict."""
        return self.__data.copy()

if "__main__" == __name__:
    ...
