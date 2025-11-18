"""Fan slider widget."""

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QSlider, QWidget

from src.utils.signals import GLOBAL_SIGNALS


class FanSlider(QSlider):
    """Fan Slider widget."""

    def __init__(self, device_id: str, channel: str, parent: QWidget|None=None) -> None:
        """Init fan slider widget."""
        super().__init__(parent=parent)
        self.setOrientation(Qt.Orientation.Vertical)
        self.setMinimum(0)
        self.setValue(30)
        self.setMaximum(100)
        self.__device_id: int = int(device_id)
        self.__channel: str = channel
        self.valueChanged.connect(self.__update_slider_style)

    @Slot(int)
    def __update_slider_style(self, new_value: int) -> None:
        """Update given QSlider style."""
        cursor: Qt.CursorShape = Qt.CursorShape.ClosedHandCursor
        lightness: int = 50
        if not self.isEnabled():
            cursor = Qt.CursorShape.ForbiddenCursor
            lightness = 30
        GLOBAL_SIGNALS.update_speed.emit(self.__device_id, self.__channel, new_value)
        self.setCursor(cursor)
        self.setStyleSheet(f"""
            QSlider::handle:vertical {{
                background: hsl(200, 100%, {lightness}%);
                border: none;
                border-radius: 10px;
                margin: 0 -6px;
                height: 20px;
                width: 20px;
            }}
            QSlider::add-page:vertical {{
                background-color: hsl({100 - new_value}, 100%, {lightness}%);
            }}
        """)

if "__main__" == __name__:
    ...
