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

    def __update_fan_source(self, device_id: str, channel: str, source: str) -> None:
        """Update fan temperature source."""
        sources: dict[str, Any] = self.__sources.get_data()
        if device_id not in sources:
            sources[device_id] = {}
        if channel not in sources[device_id]:
            sources[device_id][channel] = {}
        sources[device_id][channel] = source
        self.__sources[device_id] = sources[device_id]

    def __update_value_on_import(self, device_id: str, channel: str, source_box: QComboBox) -> None:
        """Update mode on Import."""
        source_box.setCurrentText(self.__sources[device_id][channel])

    def __curve_on_click(self, device_id: str, channel: str) -> None:
        """Curve button on click callback."""
        dialog: FanCurve = FanCurve(points=self.__curves.get(device_id, {}).get(channel, None),
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
        speed: int = int(FanCurve.evaluate(points, temp))
        slider.setValue(int(min(100, speed)))

    def __create_fan_slider(self, device_id: str, channel: str) -> FanSlider:
        """Create FAN slider."""
        fan_slider: FanSlider = FanSlider(device_id, channel, parent=self.parentWidget())
        self.__temps.value_changed.connect(lambda temps: self.__change_slider_value(temps,
                                                                                    fan_slider,
                                                                                    device_id,
                                                                                    channel))
        return fan_slider

    def __create_fan_settings(self, device_id: str, channel: str) -> QGridLayout:
        """Create fan settings layout."""
        fan_settings: QGridLayout = QGridLayout()
        fan_settings.addWidget(utils.create_label("Source"), 0, 0,
                               alignment=Qt.AlignmentFlag.AlignRight)
        source_box: QComboBox = QComboBox()
        source_box.addItems([*self.__temps.get_data().keys()])
        source_box.currentTextChanged.connect(lambda source: self.__update_fan_source(device_id,
                                                                                      channel,
                                                                                      source))
        current_text: str = source_box.currentText()
        if device_id in self.__sources and channel in self.__sources[device_id]:
            current_text = self.__sources[device_id][channel]
            source_box.setCurrentText(current_text)
        fan_settings.addWidget(source_box, 0, 1)
        self.__update_fan_source(device_id, channel, current_text)
        GLOBAL_SIGNALS.imported.connect(lambda: self.__update_value_on_import(device_id, channel,
                                                                              source_box))
        return fan_settings

    def __create_fan_layout(self, device_id: str, channel: str) -> QVBoxLayout:
        """Create fan layout."""
        fan_layout: QVBoxLayout = QVBoxLayout()
        header_layout: QHBoxLayout = QHBoxLayout()
        channel_label: QLabel = utils.create_label(channel, target="channel")
        rpm_label: QLabel = utils.create_label("RPM: N/A")
        button: QPushButton = QPushButton("Curve")
        button.clicked.connect(lambda: self.__curve_on_click(device_id, channel))
        self.__labels[device_id][channel] = rpm_label
        header_layout.addWidget(channel_label, alignment=Qt.AlignmentFlag.AlignLeft)
        header_layout.addWidget(rpm_label, alignment=Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignRight)
        slider_layout: QHBoxLayout = QHBoxLayout()
        slider_layout.addLayout(utils.create_ruler())
        fan_slider: FanSlider = self.__create_fan_slider(device_id, channel)
        slider_layout.addWidget(fan_slider, alignment=Qt.AlignmentFlag.AlignHCenter)
        slider_layout.addLayout(utils.create_ruler(left=False))
        fan_layout.addLayout(header_layout)
        fan_layout.addLayout(slider_layout)
        fan_layout.addLayout(self.__create_fan_settings(device_id, channel))
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
