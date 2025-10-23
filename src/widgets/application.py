"""Main application."""

from PySide6.QtWidgets import QApplication


class Application(QApplication):
    """Main Application."""

    def __init__(self, app_name: str) -> None:
        """INIT."""
        super().__init__([])
        self.setApplicationName(app_name)

if "__main__" == __name__:
    ...
