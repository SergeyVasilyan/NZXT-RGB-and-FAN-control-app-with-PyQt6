"""Fan slider widget."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSlider, QWidget


class FanSlider(QSlider):
    """Fan Slider widget."""

    def __init__(self, parent: QWidget|None=None) -> None:
        """Init fan slider widget."""
        super().__init__(parent=parent)
        self.setOrientation(Qt.Orientation.Vertical)
        self.setMinimum(0)
        self.setValue(30)
        self.setMaximum(100)
        self.valueChanged.connect(self.__update_slider_style)

    def __update_slider_style(self) -> None:
       """Update given QSlider style."""
       cursor: Qt.CursorShape = Qt.CursorShape.ClosedHandCursor
       lightness: int = 50
       if not self.isEnabled():
           cursor = Qt.CursorShape.ForbiddenCursor
           lightness = 30
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
                background-color: hsl({100 - self.value()}, 100%, {lightness}%);
            }}
       """)

if "__main__" == __name__:
    ...
