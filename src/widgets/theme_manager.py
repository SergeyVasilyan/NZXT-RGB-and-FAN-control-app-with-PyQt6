"""Theme manager."""

import os
from PyQt6.QtWidgets import QApplication


class ThemeManager:
    """Theme manager"""

    def __init__(self, app: QApplication):
        self.__app: QApplication = app
        self.__path: str = "src/styles"

    def __load_stylesheet(self, name: str) -> str:
        """Load corresponding QSS."""
        path: str = f"{self.__path}/{name}.qss"
        try:
            with open(path, "r") as f:
                return f.read()
        except FileNotFoundError:
            return ""

    def get_themes(self) -> list[str]:
        """Get all available themes."""
        themes: list[str] = []
        for _, _, files in os.walk(self.__path):
            if not files:
                continue
            for file in files:
                if ".qss" in file.lower():
                    themes.append(os.path.splitext(file)[0])
        return themes

    def apply_theme(self, name: str) -> None:
        """Apply given theme."""
        qss: str = self.__load_stylesheet(name)
        if qss:
            self.__app.setStyleSheet(qss)
            self.__app.setProperty("theme", name)

if "__main__" == __name__:
    ...
