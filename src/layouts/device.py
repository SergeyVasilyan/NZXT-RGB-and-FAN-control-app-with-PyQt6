"""Device section of the app."""

from typing import Any, override

from liquidctl.driver import smart_device
import src.utils.common as utils
from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import QComboBox, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout
from src.utils.observable_dict import ObservableDict
from src.utils.signals import GLOBAL_SIGNALS
from src.widgets.fan_slider import FanSlider
from src.widgets.settings_dialog import ServerConfiguration


class Worker(QThread):
    """Worker thread that poll fans rpm at given rate."""

    def __init__(self, devices: list[smart_device.SmartDevice2],
                       sliders: dict[str, dict[str, FanSlider]],
                       server_config: ServerConfiguration) -> None:
        """INIT."""
        super().__init__()
        self.__sliders: dict[str, dict[str, FanSlider]] = sliders
        self.__number_of_sliders: int = sum(len(v) for v in sliders.values())
        self.__devices: list[smart_device.SmartDevice2] = devices
        self.__config: ServerConfiguration = server_config

    def __update_fans_speed(self) -> None:
        """Update fan speed."""
        for device_id, channels in self.__sliders.items():
            device: Any = self.__devices[int(device_id)]
            for channel, slider in channels.items():
                try:
                    device.set_fixed_speed(channel, slider.value())
                    self.msleep(self.__config.rate // self.__number_of_sliders)
                except ValueError:
                    ...

    @override
    def run(self) -> None:
        """Run the worker."""
        while True:
            self.__update_fans_speed()

class DeviceSection(QHBoxLayout):
    """Device section."""

    def __init__(self, devices: list[smart_device.SmartDevice2], modes: ObservableDict,
                       sources: ObservableDict, temps: ObservableDict, min_temp: int,
                       server_config: ServerConfiguration) -> None:
        """INIT."""
        super().__init__()
        self.__min_temp: int = min_temp
        self.__sliders: dict[str, dict[str, FanSlider]] = {}
        self.__devices: list[smart_device.SmartDevice2] = devices
        self.__modes: ObservableDict = modes
        self.__sources: ObservableDict = sources
        self.__temps: ObservableDict = temps
        self.__labels: dict[str, dict[str, QLabel]] = {}
        self.__construct_layout()
        self.__worker: Worker = Worker(self.__devices, self.__sliders, server_config)
        self.__worker.start()
        GLOBAL_SIGNALS.update_rpm.connect(self.__update_fan_rpm)

    def __update_fan_rpm(self, device_id: str, channel: str, value: int) -> None:
        """Update fan rpm report."""
        self.__labels.get(device_id, {}).get(channel, QLabel()).setText(f"RPM: {value}")

    def __update_fan_mode(self, device_id: str, channel: str, mode: str) -> None:
        """Update fan speed calculation mode."""
        modes: dict[str, Any] = self.__modes.get_data()
        if device_id not in modes:
            modes[device_id] = {}
        if channel not in modes[device_id]:
            modes[device_id][channel] = {}
        modes[device_id][channel] = mode
        self.__modes[device_id] = modes[device_id]

    def __update_fan_source(self, device_id: str, channel: str, source: str) -> None:
        """Update fan temperature source."""
        sources: dict[str, Any] = self.__sources.get_data()
        if device_id not in sources:
            sources[device_id] = {}
        if channel not in sources[device_id]:
            sources[device_id][channel] = {}
        sources[device_id][channel] = source
        self.__sources[device_id] = sources[device_id]

    def __update_value_on_import(self, device_id: str, channel: str, mode_box: QComboBox,
                                       source_box: QComboBox) -> None:
        """Update mode on Import."""
        mode_box.setCurrentText(self.__modes[device_id][channel])
        source_box.setCurrentText(self.__sources[device_id][channel])

    @staticmethod
    def __get_channel_mode(new_modes: dict[str, Any]|ObservableDict, device_id: str,
                           channel: str) -> str:
        """Change Source box state."""
        if device_modes := new_modes[device_id]:
            return device_modes.get(channel, "")
        return ""

    def __calculate_fan_speed(self, device_id: str, channel: str, temps: dict[str, Any],
                                    channel_mode: str) -> int:
        """Calculate fan speed."""
        if not channel_mode:
            return self.__min_temp
        device_sources: dict[str, Any] = self.__sources[device_id]
        if not device_sources:
            return self.__min_temp
        source: str = device_sources.get(channel, "")
        if not source:
            return self.__min_temp
        max_temp: int = 80
        noise: int = 20
        power: float = 1.0
        temp: int = max(self.__min_temp, min(int(temps[source]), max_temp))
        if "Aggressive" == channel_mode:
            noise = 10
            power = 0.5
        elif "Silent" == channel_mode:
            power = 1.5
        difference: int = max_temp - noise
        return self.__min_temp + ((temp - noise) / difference) ** power * difference

    def __change_slider_state(self, new_modes: dict[str, Any], slider: FanSlider, device_id: str,
                                    channel: str) -> None:
        """Change Source box state."""
        slider.setEnabled("Custom" == self.__get_channel_mode(new_modes, device_id, channel))

    def __change_slider_value(self, temps: dict[str, Any], slider: FanSlider, device_id: str,
                                    channel: str) -> None:
        """Change Source box state."""
        channel_mode: str = self.__get_channel_mode(self.__modes, device_id, channel)
        if "Custom" == channel_mode:
            return
        speed: int = self.__calculate_fan_speed(device_id, channel, temps, channel_mode)
        slider.setValue(int(min(100, speed)))

    def __create_fan_slider(self, device_id: str, channel: str) -> FanSlider:
        """Create FAN slider."""
        fan_slider: FanSlider = FanSlider()
        self.__modes.value_changed.connect(lambda modes: self.__change_slider_state(modes,
                                                                                    fan_slider,
                                                                                    device_id,
                                                                                    channel))
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
        fan_settings.addWidget(utils.create_label("Mode"), 1, 0,
                               alignment=Qt.AlignmentFlag.AlignRight)
        mode_box: QComboBox = QComboBox()
        mode_box.addItems(["Normal", "Aggressive", "Silent", "Custom"])
        mode_box.currentTextChanged.connect(lambda mode: self.__update_fan_mode(device_id,
                                                                                channel,
                                                                                mode))
        current_text: str = mode_box.currentText()
        if device_id in self.__modes and channel in self.__modes[device_id]:
            current_text = self.__modes[device_id][channel]
            mode_box.setCurrentText(current_text)
        self.__update_fan_mode(device_id, channel, current_text)
        GLOBAL_SIGNALS.imported.connect(lambda: self.__update_value_on_import(device_id, channel,
                                                                              mode_box, source_box))
        fan_settings.addWidget(mode_box, 1, 1)
        return fan_settings

    def __create_fan_layout(self, device_id: str, channel: str) -> QVBoxLayout:
        """Create fan layout."""
        fan_layout: QVBoxLayout = QVBoxLayout()
        header_layout: QHBoxLayout = QHBoxLayout()
        channel_label: QLabel = utils.create_label(channel, target="channel")
        rpm_label: QLabel = utils.create_label("RPM: N/A")
        self.__labels[device_id][channel] = rpm_label
        header_layout.addWidget(channel_label, alignment=Qt.AlignmentFlag.AlignLeft)
        header_layout.addWidget(rpm_label, alignment=Qt.AlignmentFlag.AlignRight)
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
