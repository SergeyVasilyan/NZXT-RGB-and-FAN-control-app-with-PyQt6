"""Device section of the app."""

from typing import Any

from liquidctl.driver import smart_device
import src.utils.common as utils
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QComboBox, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout
from src.utils.observable_dict import ObservableDict
from src.utils.signals import GLOBAL_SIGNALS
from src.widgets.curve import FanCurve, FanCurvePoint
from src.widgets.fan_slider import FanSlider


class DeviceSection(QHBoxLayout):
    """Device section."""

    def __init__(self, devices: list[smart_device.SmartDevice2], sources: ObservableDict,
                       temps: ObservableDict, curves: dict[str, dict[str, list[FanCurvePoint]]],
                       min_temp: int) -> None:
        """INIT."""
        super().__init__()
        self.__min_temp: int = min_temp
        self.__sliders: dict[str, dict[str, FanSlider]] = {}
        self.__devices: list[smart_device.SmartDevice2] = devices
        self.__sources: ObservableDict = sources
        self.__temps: ObservableDict = temps
        self.__labels: dict[str, dict[str, QLabel]] = {}
        self.__curves: dict[str, dict[str, list[FanCurvePoint]]] = curves
        self.__construct_layout()
        GLOBAL_SIGNALS.update_rpm.connect(self.__update_fan_rpm)

    @property
    def curves(self) -> dict[str, dict[str, list[FanCurvePoint]]]:
        """Return current fan curves."""
        return self.__curves

    @Slot(int, str, int)
    def __update_fan_rpm(self, device_id: int, channel: str, value: int) -> None:
        """Update fan rpm report."""
        self.__labels.get(str(device_id), {}).get(channel, QLabel()).setText(f"RPM: {value}")

    def __update_value_on_import(self, device_id: str, channel: str, source_box: QComboBox) -> None:
        """Update mode on Import."""
        source_box.setCurrentText(self.__sources[device_id][channel])

    def __curve_on_click(self, device_id: str, channel: str) -> None:
        """Curve button on click callback."""
        dialog: FanCurve = FanCurve(self.__temps, self.__sources, device_id, channel,
                                    points=self.__curves.get(device_id, {}).get(channel, None),
                                    parent=self.parentWidget())
        dialog.exec()
        if device_id not in self.__curves:
            self.__curves[device_id] = {}
        self.__curves[device_id][channel] = dialog.points

    def __change_slider_value(self, temps: dict[str, Any], slider: FanSlider, device_id: str,
                                    channel: str) -> None:
        """Change Source box state."""
        device_sources: dict[str, Any] = self.__sources[device_id]
        if not device_sources:
            return
        source: str = device_sources.get(channel, "")
        temp: float = max(self.__min_temp, temps.get(source, .0))
        points: list[FanCurvePoint] = self.__curves.get(device_id, {}).get(channel, [])
        slider.setValue(int(min(100, int(FanCurve.evaluate(points, temp)))))

    def __create_fan_slider(self, device_id: str, channel: str) -> FanSlider:
        """Create FAN slider."""
        fan_slider: FanSlider = FanSlider(device_id, channel, parent=self.parentWidget())
        self.__temps.value_changed.connect(lambda temps: self.__change_slider_value(temps,
                                                                                    fan_slider,
                                                                                    device_id,
                                                                                    channel))
        return fan_slider

    def __create_fan_layout(self, device_id: str, channel: str) -> QVBoxLayout:
        """Create fan layout."""
        fan_layout: QVBoxLayout = QVBoxLayout()
        header_layout: QHBoxLayout = QHBoxLayout()
        channel_label: QLabel = utils.create_label(channel, target="channel")
        rpm_label: QLabel = utils.create_label("RPM: N/A")
        self.__labels[device_id][channel] = rpm_label
        header_layout.addWidget(channel_label, alignment=Qt.AlignmentFlag.AlignLeft)
        header_layout.addWidget(rpm_label, alignment=Qt.AlignmentFlag.AlignCenter)
        slider_layout: QHBoxLayout = QHBoxLayout()
        slider_layout.addLayout(utils.create_ruler())
        fan_slider: FanSlider = self.__create_fan_slider(device_id, channel)
        slider_layout.addWidget(fan_slider, alignment=Qt.AlignmentFlag.AlignHCenter)
        slider_layout.addLayout(utils.create_ruler(left=False))
        button: QPushButton = QPushButton("Curve")
        button.clicked.connect(lambda: self.__curve_on_click(device_id, channel))
        fan_layout.addLayout(header_layout)
        fan_layout.addLayout(slider_layout)
        fan_layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
        if device_id not in self.__sliders:
            self.__sliders[device_id] = {}
        self.__sliders[device_id][channel] = fan_slider
        return fan_layout

    def __create_device_layout(self, device: Any, device_id: str) -> QVBoxLayout:
        """Create Device Layout."""
        self.__labels[device_id] = {}
        layout: QVBoxLayout = QVBoxLayout()
        name: QLabel = utils.create_label(device.description, target="device")
        layout.addWidget(name, alignment=Qt.AlignmentFlag.AlignCenter)
        fans_layout: QHBoxLayout = QHBoxLayout()
        channels: list[str] = list(device._speed_channels.keys())
        for channel in channels:
            fans_layout.addLayout(self.__create_fan_layout(device_id, channel))
            if channel != channels[-1]:
                fans_layout.addWidget(utils.create_separator())
        layout.addLayout(fans_layout)
        return layout

    def __construct_layout(self) -> None:
        """Construct layout."""
        for device_id, device in enumerate(self.__devices):
            self.addLayout(self.__create_device_layout(device, str(device_id)))
            if device != self.__devices[-1]:
                self.addWidget(utils.create_separator())
