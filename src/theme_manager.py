"""Theme manager."""

from PyQt6.QtWidgets import QApplication

class ThemeManager:
    """Theme manager"""

    def __init__(self, app: QApplication):
        self.__app: QApplication = app
        self.__path: str = "styles"

    def __load_stylesheet(self, name: str) -> str:
        """Load corresponding QSS."""
        path: str = f"{self.__path}/{name}.qss"
        try:
            with open(path, "r") as f:
                return f.read()
        except FileNotFoundError:
            return ""

    def apply_theme(self, name: str) -> None:
        """Apply given theme."""
        qss: str = self.__load_stylesheet(name)
        if qss:
            self.__app.setStyleSheet(qss)
            self.__app.setProperty("theme", name)

if "__main__" == __name__:
    ...
