"""Common functions between all modules."""

import os
from enum import StrEnum

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)


class PathManager(StrEnum):
    """Path Manager class."""

    SOURCE = "src"
    ICONS = os.path.join(SOURCE, "icons")
    PRESETS = os.path.join(SOURCE, "presets")

def create_separator(horizontal: bool=False) -> QFrame:
    """Create separator."""
    separator: QFrame = QFrame()
    separator.setFrameShape(QFrame.Shape.HLine if horizontal else QFrame.Shape.VLine)
    separator.setFrameShadow(QFrame.Shadow.Sunken)
    separator.setLineWidth(1)
    return separator

def force_refresh(widget: QWidget) -> None:
    """Force refresh widget style."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()

def create_label(text: str, size: str="", target: str="") -> QLabel:
    """Create QLabel with dynamic QSS."""
    size_map: dict[str, int] = {
        "small": 10,
        "medium": 30,
        "large": 50 ,
    }
    label: QLabel = QLabel(text)
    font: QFont = label.font()
    font.setPointSize(size_map.get(size, size_map["small"]))
    label.setFont(font)
    if target:
        label.setProperty("for", target)
    force_refresh(label)
    return label

def create_icon(name: str, theme: str) -> QIcon:
    """Create themed QIcon."""
    if not name:
        return QIcon()
    pixmap: QPixmap = QPixmap(f"{PathManager.ICONS}/{name}.png")
    if pixmap.isNull():
        return QIcon()
    painter: QPainter = QPainter()
    if painter.begin(pixmap):
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor("white" if "dark" in theme  else "black"))
        painter.end()
    return QIcon(pixmap)

def create_ruler(min_val: int=0, max_val: int=100, step: int=10, left: bool=True) -> QVBoxLayout:
    """Create ruler."""
    layout: QVBoxLayout = QVBoxLayout()
    layout.setSpacing(0)
    layout.setContentsMargins(0, 0, 0, 0)
    values: list[int] = list(reversed(range(min_val, max_val + 1, step)))
    for i, value in enumerate(values):
        step_layout: QHBoxLayout = QHBoxLayout()
        label = QLabel(str(value))
        alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignVCenter
        alignment |= Qt.AlignmentFlag.AlignLeft if left else Qt.AlignmentFlag.AlignRight
        if left:
            step_layout.addWidget(label, alignment=alignment)
            step_layout.addWidget(create_separator(horizontal=True))
        else:
            step_layout.addWidget(create_separator(horizontal=True))
            step_layout.addWidget(label, alignment=alignment)
        if i and i < len(values):
            layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum,
                                             QSizePolicy.Policy.Expanding))
        layout.addLayout(step_layout)
    return layout
