"""Fan-curve widget."""

from dataclasses import dataclass
from typing import override

import src.utils.common as utils
from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt, Signal, Slot
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from src.utils.observable_dict import ObservableDict
from src.utils.signals import GLOBAL_SIGNALS
from typing_extensions import Any


@dataclass(order=True, frozen=False)
class FanCurvePoint:
    """A single fan-curve control point in domain units (temperature, percent)."""

    temperature: float
    percent: float

    def clamp(self, t_min: float, t_max: float, p_min: float, p_max: float) -> None:
        """Clamp new values."""
        self.temperature = round(max(t_min, min(t_max, self.temperature)), 2)
        self.percent = round(max(p_min, min(p_max, self.percent)), 2)


class FanCurveWidget(QWidget):
    """Interactive fan-curve widget."""

    def __init__(self, points: list[FanCurvePoint]|None=None, parent: QWidget|None=None) -> None:
        """Initialize Fan Curve widget."""
        super().__init__(parent)
        self.__t_min: float = 30.0
        self.__t_max: float = 85.0
        self.__p_min: float = .0
        self.__p_max: float = 100.0
        self.__t: FanCurvePoint = FanCurvePoint(temperature=self.__t_min, percent=self.__p_min)
        self.__padding: int = 28
        self.__point_radius: int = 6
        self.__snap_epsilon_px: int = 8
        self.__bg: QColor = QColor(40, 40, 40)
        self.__grid: QColor = QColor(80, 80, 80)
        self.__axis: QColor = QColor(180, 180, 190)
        self.__curve: QColor = QColor(80, 180, 250)
        self.__point_fill: QColor = QColor(255, 255, 255)
        self.__point_border: QColor = QColor(255, 255, 255)
        self.__points: list[FanCurvePoint] = []
        if points is None:
            number_of_points: int = 4
            temperature_step: float = round((self.__t_max - self.__t_min) / number_of_points, 2)
            percentage_step: float = round((self.__p_max - self.__p_min) / number_of_points, 2)
            temperature: float = self.__t_min
            percentage: float = self.__p_min
            for _ in range(number_of_points + 1):
                self.__points.append(FanCurvePoint(temperature, percentage))
                temperature += temperature_step
                percentage += percentage_step
        else:
            for point in points:
                point.clamp(self.__t_min, self.__t_max, self.__p_min, self.__p_max)
                self.__points.append(point)
        self.__drag_index: int|None = None
        self.setMinimumSize(QSize(360, 220))
        self.setMouseTracking(True)

    @property
    def points(self) -> list[FanCurvePoint]:
        """Return fan curve points."""
        return self.__points.copy()

    @Slot(list)
    def set_points(self, points: list[FanCurvePoint]) -> None:
        """Set curve points; clamps to ranges and keeps them sorted."""
        clamped: list[FanCurvePoint] = []
        for point in points:
            curve_point: FanCurvePoint = FanCurvePoint(point.temperature, point.percent)
            curve_point.clamp(self.__t_min, self.__t_max, self.__p_min, self.__p_max)
            clamped.append(curve_point)
        clamped.sort(key=lambda p: p.temperature)
        self.__points = clamped
        self.update()

    @Slot(FanCurvePoint)
    def update_temperature(self, point: FanCurvePoint) -> None:
        """Update current temperature."""
        point.clamp(self.__t_min, self.__t_max, self.__p_min, self.__p_max)
        self.__t = point
        self.update()

    def __add_point(self, temperature: float, percent: float) -> None:
        """Add a point and keep the list sorted."""
        point: FanCurvePoint = FanCurvePoint(temperature, percent)
        point.clamp(self.__t_min, self.__t_max, self.__p_min, self.__p_max)
        self.__points.append(point)
        self.__points.sort(key=lambda p: p.temperature)
        self.update()

    def __remove_point_at_index(self, index: int) -> None:
        """Remove point by index; safe no-op if index invalid."""
        if 0 <= index < len(self.__points):
            self.__points.pop(index)
            self.update()

    def __to_screen(self, rect: QRectF, point: FanCurvePoint) -> QPointF:
        """Map domain point to screen coordinates."""
        x: float = 0.0
        y: float = 0.0
        if self.__t_max > self.__t_min:
            x = (point.temperature - self.__t_min) / (self.__t_max - self.__t_min)
        if self.__p_max > self.__p_min:
            y = (point.percent - self.__p_min) / (self.__p_max - self.__p_min)
        x = rect.left() + x * rect.width()
        y = rect.bottom() - y * rect.height()
        return QPointF(x, y)

    def __from_screen(self, rect: QRectF, position: QPointF) -> FanCurvePoint:
        """Map screen position to domain point."""
        x: float = 0.0
        y: float = 0.0
        if rect.width() > 0:
            x = (position.x() - rect.left()) / rect.width()
        if rect.height() > 0:
            y = (rect.bottom() - position.y()) / rect.height()
        temperature: float = round(self.__t_min + x * (self.__t_max - self.__t_min), 2)
        percent: float = round(self.__p_min + y * (self.__p_max - self.__p_min), 2)
        return FanCurvePoint(temperature, percent)

    def __hit_test(self, position: QPointF) -> int|None:
        """Return index of point under cursor, if any."""
        plot: QRectF = self.__plot_rect()
        for index, point in enumerate(self.__points):
            center: QPointF = self.__to_screen(plot, point)
            dx: float = center.x() - position.x()
            dy: float = center.y() - position.y()
            if (dx * dx + dy * dy) ** 0.5 <= max(self.__point_radius + 2, self.__snap_epsilon_px):
                return index
        return None

    def __plot_rect(self) -> QRectF:
        """Plot rectangle."""
        rect: QRect = self.rect()
        return QRectF(rect.left() + self.__padding, rect.top() + self.__padding,
                      rect.width() - 2 * self.__padding, rect.height() - 2 * self.__padding)

    def __draw_grid(self, painter: QPainter, rect: QRectF) -> None:
        """Draw grid."""
        painter.save()
        painter.setPen(QPen(self.__grid, 1, Qt.PenStyle.DotLine))
        for i in range(6):
            x: int = int(rect.left() + (rect.width() * i / 5.0))
            painter.drawLine(x, int(rect.top()), x, int(rect.bottom()))
            y: int = int(rect.top() + (rect.height() * i / 5.0))
            painter.drawLine(int(rect.left()), y, int(rect.right()), y)
        painter.restore()

    def __draw_axes(self, painter: QPainter, rect: QRectF) -> None:
        """Draw axes."""
        painter.save()
        painter.setPen(QPen(self.__axis, 2))
        painter.drawRect(rect)
        painter.restore()

    def __draw_curve(self, painter: QPainter, rect: QRectF) -> None:
        """Draw curve."""
        if 2 > len(self.__points):
            return
        painter.save()
        painter.setPen(QPen(self.__curve, 2))
        points: list[FanCurvePoint] = sorted(self.__points, key=lambda x: x.temperature)
        for i in range(len(points) - 1):
            painter.drawLine(self.__to_screen(rect, points[i]), self.__to_screen(rect, points[i+1]))
        painter.restore()

    def __draw_filled_point(self, painter: QPainter, rect: QRectF, point: FanCurvePoint,
                                  color: QColor) -> QPointF:
        """Draw filled point and return center."""
        painter.setPen(QPen(color, 2))
        painter.setBrush(color)
        center: QPointF = self.__to_screen(rect, point)
        painter.drawEllipse(center, self.__point_radius, self.__point_radius)
        return center

    def __draw_text_above_point(self, painter: QPainter, rect: QRectF, label: QLabel,
                                      center: QPointF, color: QColor) -> None:
        """Draw text above given point."""
        painter.setPen(QPen(color, 1))
        label_width: int = label.fontMetrics().boundingRect(label.text()).width()
        x: int = int(center.x() + self.__point_radius + 2)
        y: int = int(center.y() - self.__point_radius - 2)
        painter.drawText(min(x, int(rect.width() - (label_width / 2))), y, label.text())

    def __draw_temperature_lines(self, painter: QPainter, rect: QRectF) -> None:
        """Draw temperature lines."""
        painter.save()
        label: QLabel = QLabel(f"[T: {self.__t.temperature}, P: {self.__t.percent}]")
        color: QColor = QColor.fromHsl(int(100 - self.__t.temperature), 255, 125)
        center: QPointF = self.__draw_filled_point(painter, rect, self.__t, color)
        self.__draw_text_above_point(painter, rect, label, center, color)
        painter.restore()

    def __draw_points(self, painter: QPainter, rect: QRectF) -> None:
        """Draw points."""
        painter.save()
        for index, point in enumerate(self.__points, start=1):
            center: QPointF = self.__draw_filled_point(painter, rect, point, self.__point_fill)
            label: QLabel = QLabel(f"{index} [T: {point.temperature}, P: {point.percent}]")
            self.__draw_text_above_point(painter, rect, label, center, self.__axis)
        painter.restore()

    def __draw_labels(self, painter: QPainter, rect: QRectF) -> None:
        """Draw labels."""
        painter.save()
        painter.setPen(self.__axis)
        painter.drawText(int(rect.left()), int(rect.top() - 8), "Fan curve")
        painter.drawText(int(rect.left()), int(rect.bottom() + 16),
                         f"Temperature (°C) [{self.__t_min}..{self.__t_max}]")
        painter.rotate(-90)
        painter.drawText(int(-rect.bottom()), int(rect.left() - 12),
                         f"Percent (%) [{self.__p_min}..{self.__p_max}]")
        painter.restore()

    @override
    def paintEvent(self, _event: QPaintEvent) -> None:
        """Override paint event."""
        painter: QPainter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), self.__bg)
        plot_rect: QRectF = self.__plot_rect()
        self.__draw_grid(painter, plot_rect)
        self.__draw_axes(painter, plot_rect)
        self.__draw_curve(painter, plot_rect)
        self.__draw_temperature_lines(painter, plot_rect)
        self.__draw_points(painter, plot_rect)
        self.__draw_labels(painter, plot_rect)

    @override
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Override mouse press event."""
        if Qt.MouseButton.LeftButton == event.button():
            index: int|None = self.__hit_test(event.position())
            if index is not None:
                self.__drag_index = index
            else:
                plot: QRectF = self.__plot_rect()
                point: FanCurvePoint = self.__from_screen(plot, event.position())
                self.__add_point(point.temperature, point.percent)
        elif Qt.MouseButton.RightButton == event.button():
            index: int|None = self.__hit_test(event.position())
            if index is not None:
                self.__remove_point_at_index(index)

    @override
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Override mouse move event."""
        if self.__drag_index is None:
            return
        plot: QRectF = self.__plot_rect()
        point: FanCurvePoint = self.__from_screen(plot, event.position())
        left_bound: float = self.__t_min
        right_bound: float = self.__t_max
        if self.__drag_index - 1 >= 0:
            left_bound = max(left_bound, self.__points[self.__drag_index - 1].temperature + 0.01)
        if self.__drag_index + 1 < len(self.__points):
            right_bound = min(right_bound, self.__points[self.__drag_index + 1].temperature - 0.01)
        self.__points[self.__drag_index].temperature = max(left_bound,
                                                           min(right_bound, point.temperature))
        self.__points[self.__drag_index].percent = max(self.__p_min,
                                                       min(self.__p_max, point.percent))
        self.update()

    @override
    def mouseReleaseEvent(self, _event: QMouseEvent) -> None:
        """Override mouse release event."""
        self.__drag_index = None

class FanCurve(QWidget):
    """Fan curve dialog."""

    __update_points: Signal = Signal(list)
    __update_temperature: Signal = Signal(FanCurvePoint)
    __point_separator: str = ","
    __list_separator: str = "|"

    def __init__(self, temps: ObservableDict, sources: ObservableDict,
                       device_id: str, channel: str, points: list[FanCurvePoint]|None=None,
                       parent: QWidget|None=None) -> None:
        """Initialize fan curve dialog."""
        super().__init__(parent)
        self.__device_id: str = device_id
        self.__channel: str = channel
        self.__temps: ObservableDict = temps
        self.__sources: ObservableDict = sources
        self.__rpm_label: QLabel = utils.create_label("RPM: N/A")
        self.__widget: FanCurveWidget = FanCurveWidget(points=points, parent=self)
        self.__update_points.connect(self.__widget.set_points)
        self.__update_temperature.connect(self.__widget.update_temperature)
        self.__temps.value_changed.connect(self.__update_temperature_line)
        self.__construct_layout()
        GLOBAL_SIGNALS.update_rpm.connect(self.__update_fan_rpm)

    @Slot(int, str, int)
    def __update_fan_rpm(self, device_id: int, channel: str, value: int) -> None:
        """Update fan rpm report."""
        if str(device_id) == self.__device_id and channel == self.__channel:
            self.__rpm_label.setText(f"RPM: {value}")

    @property
    def points(self) -> list[FanCurvePoint]:
        """Return fan curve points."""
        return self.__widget.points

    @classmethod
    def evaluate(cls, points: list[FanCurvePoint], temperature: float) -> float:
        """Evaluate the curve (linear interpolation) at given temperature."""
        if not points:
            return .0
        points = sorted(points, key=lambda p: p.temperature)
        if temperature <= points[0].temperature:
            return points[0].percent
        if temperature >= points[-1].temperature:
            return points[-1].percent
        for index in range(len(points) - 1):
            current_point: FanCurvePoint = points[index]
            next_point: FanCurvePoint = points[index + 1]
            if current_point.temperature <= temperature <= next_point.temperature:
                if current_point.temperature == next_point.temperature:
                    return current_point.percent
                temperature = ((temperature - current_point.temperature)
                                / (next_point.temperature - current_point.temperature))
                return (current_point.percent + temperature
                        * (next_point.percent - current_point.percent))
        return points[-1].percent

    @classmethod
    def convert_points_to_str(cls, points: list[FanCurvePoint]) -> str:
        """Convert points to str."""
        converted_points: list[str] = []
        for point in points:
            converted_points.append(f"{point.temperature}{cls.__point_separator}{point.percent}")
        return cls.__list_separator.join(converted_points)

    @classmethod
    def convert_str_to_points(cls, text: str) -> list[FanCurvePoint]:
        """Convert string to Fan Curve points."""
        if cls.__list_separator not in text or cls.__point_separator not in text:
            return []
        points: list[FanCurvePoint] = []
        try:
            for info in text.split(cls.__list_separator):
                temperature, percent = info.split(cls.__point_separator)
                points.append(FanCurvePoint(temperature=float(temperature), percent=float(percent)))
        except Exception:
            return []
        return points

    def __update_temperature_line(self) -> None:
        """Update temperature line."""
        device_sources: dict[str, Any] = self.__sources[self.__device_id]
        if not device_sources:
            return
        source: str = device_sources.get(self.__channel, "")
        temperature: float = self.__temps[source]
        speed: float = self.evaluate(self.__widget.points, temperature)
        GLOBAL_SIGNALS.update_speed.emit(int(self.__device_id), self.__channel, int(speed))
        self.__update_temperature.emit(FanCurvePoint(temperature=temperature, percent=speed))

    def __copy_on_click(self) -> None:
        """Copy current curve to clipboard."""
        QGuiApplication.clipboard().setText(self.convert_points_to_str(self.__widget.points))

    def __paste_on_click(self) -> None:
        """Paste clipboard curve information."""
        self.__update_points.emit(self.convert_str_to_points(QGuiApplication.clipboard().text()))

    def __update_fan_source(self, source: str) -> None:
        """Update fan temperature source."""
        sources: dict[str, Any] = self.__sources.get_data()
        if self.__device_id not in sources:
            sources[self.__device_id] = {}
        if self.__channel not in sources[self.__device_id]:
            sources[self.__device_id][self.__channel] = {}
        sources[self.__device_id][self.__channel] = source
        self.__sources[self.__device_id] = sources[self.__device_id]

    def __construct_source_layout(self) -> QGridLayout:
        """Create fan settings layout."""
        layout: QGridLayout = QGridLayout()
        source_box: QComboBox = QComboBox()
        source_box.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        source_box.addItems([*self.__temps.get_data().keys()])
        source_box.currentTextChanged.connect(self.__update_fan_source)
        current_text: str = source_box.currentText()
        if self.__device_id in self.__sources\
            and self.__channel in self.__sources[self.__device_id]:
            current_text = self.__sources[self.__device_id][self.__channel]
            source_box.setCurrentText(current_text)
        layout.addWidget(utils.create_label(self.__channel, target="channel"), 0, 0,
                                            alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(source_box, 0, 1, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.__rpm_label, 0, 2, alignment=Qt.AlignmentFlag.AlignRight)
        self.__update_fan_source(current_text)
        return layout

    def __construct_buttons_layout(self) -> QHBoxLayout:
        """Construct buttons layout."""
        layout: QHBoxLayout = QHBoxLayout()
        layout.setContentsMargins(0, 5, 0, 5)
        copy_button: QPushButton = QPushButton(QIcon.fromTheme("edit-copy"), "Copy")
        paste_button: QPushButton = QPushButton(QIcon.fromTheme("edit-paste"), "Paste")
        copy_button.clicked.connect(self.__copy_on_click)
        paste_button.clicked.connect(self.__paste_on_click)
        layout.addWidget(copy_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(paste_button, alignment=Qt.AlignmentFlag.AlignCenter)
        return layout

    def __construct_layout(self) -> None:
        """Construct layout."""
        layout: QVBoxLayout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(self.__construct_source_layout(), stretch=0)
        layout.addWidget(self.__widget, stretch=1)
        layout.addLayout(self.__construct_buttons_layout(), stretch=0)
        self.setLayout(layout)

if "__main__" == __name__:
    ...
