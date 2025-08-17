"""Device section of the app."""

from typing import Any

import src.utils.common as utils
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QSlider, QVBoxLayout
from src.utils.common import ImportSignal
from src.utils.observable_dict import ObservableDict


class DeviceSection(QHBoxLayout):
    """Device section."""

    def __init__(self, devices: list[Any], modes: ObservableDict, sources: ObservableDict,
                       temps: ObservableDict, update_signal: ImportSignal, min_temp: int) -> None:
        """INIT."""
        super().__init__()
        self.__devices: list[Any] = devices
        self.__modes: ObservableDict = modes
        self.__sources: ObservableDict = sources
        self.__temps: ObservableDict = temps
        self.__update_signal: ImportSignal = update_signal
        self.__min_temp: int = min_temp
        for device_id, device in enumerate(self.__devices):
            self.addLayout(self.__create_device_layout(device, str(device_id)))
            if device != self.__devices[-1]:
                self.addWidget(utils.create_separator())

    def __update_slider_style(self, slider: QSlider, value: int) -> None:
        """Update given QSlider style."""
        is_enabled: bool = slider.isEnabled()
        cursor: Qt.CursorShape = Qt.CursorShape.ClosedHandCursor
        if not is_enabled:
            cursor = Qt.CursorShape.ForbiddenCursor
        slider.setCursor(cursor)
        lightness: int = 50 if is_enabled else 30
        slider.setStyleSheet(f"""
            QSlider::handle:vertical {{
                background: hsl(200, 100%, {lightness}%);
                border: none;
                border-radius: 10px;
                margin: 0 -6px;
                height: 20px;
                width: 20px;
            }}
            QSlider::add-page:vertical {{
                background-color: hsl({100 - value}, 100%, {lightness}%);
            }}
        """)

    def __update_fan_speed(self, device_id: str, channel: str, value: int,
                                 fan_slider: QSlider) -> None:
        """Set Fan speed to corresponding value."""
        try:
            self.__devices[int(device_id)].set_fixed_speed(channel, value)
        except ValueError:
            print(f"ERROR: Failed to set fan speed for {device_id=} {channel=}")
        self.__update_slider_style(fan_slider, value)

    def __update_fan_mode(self, device_id: str, channel: str, mode: str) -> None:
        modes: dict[str, Any] = self.__modes.get_data()
        if device_id not in modes:
            modes[device_id] = {}
        modes[device_id][channel] = mode
        self.__modes[device_id] = modes[device_id]

    def __update_fan_source(self, device_id: str, channel: str, source: str) -> None:
        sources: dict[str, Any] = self.__sources.get_data()
        if device_id not in sources:
            sources[device_id] = {}
        sources[device_id][channel] = source
        self.__sources[device_id] = sources[device_id]

    @staticmethod
    def __get_channel_mode(new_modes: dict[str, Any]|ObservableDict, device_id: str,
                           channel: str) -> str:
        """Change Source box state."""
        device_modes: dict[str, Any] = new_modes[device_id]
        if not device_modes:
            return ""
        return device_modes.get(channel, "")

    def __change_slider_state(self, new_modes: dict[str, Any], slider: QSlider, device_id: str,
                                    channel: str) -> None:
        """Change Source box state."""
        channel_mode: str = self.__get_channel_mode(new_modes, device_id, channel)
        if not channel_mode:
            return
        slider.setEnabled("Custom" == channel_mode)
        self.__update_slider_style(slider, slider.value())

    def __change_slider_value(self, temps: dict[str, Any], slider: QSlider, device_id: str,
                                    channel: str) -> None:
        """Change Source box state."""
        channel_mode: str = self.__get_channel_mode(self.__modes, device_id, channel)
        if not channel_mode:
            return
        if "Custom" != channel_mode:
            device_sources: dict[str, Any] = self.__sources[device_id]
            if not device_sources:
                return
            source: str = device_sources.get(channel, "")
            if not source:
                return
            temp: int = max(self.__min_temp, min(int(temps[source]), 90))
            speed: int = min(100, self.__min_temp + ((temp - 20) / 70) ** 1.0 * 70)
            if "Aggressive" == channel_mode:
                speed = min(100, self.__min_temp + ((temp - 20) / 70) ** 0.5 * 70)
            elif "Silent" == channel_mode:
                speed = min(100, self.__min_temp + ((temp - 20) / 70) ** 1.5 * 70)
            speed = int(min(speed, 100))
            slider.setValue(speed)
            self.__update_slider_style(slider, speed)

    def __create_fan_slider(self, device_id: str, channel: str) -> QSlider:
        """Create FAN slider."""
        fan_slider: QSlider = QSlider(Qt.Orientation.Vertical)
        fan_slider.setMinimum(0)
        fan_slider.setValue(30)
        fan_slider.setMaximum(100)
        fan_slider.valueChanged.connect(lambda value: self.__update_fan_speed(device_id, channel,
                                                                              value, fan_slider))
        self.__modes.value_changed.connect(lambda modes: self.__change_slider_state(modes,
                                                                                    fan_slider,
                                                                                    device_id,
                                                                                    channel))
        self.__temps.value_changed.connect(lambda temps: self.__change_slider_value(temps,
                                                                                    fan_slider,
                                                                                    device_id,
                                                                                    channel))
        self.__update_slider_style(fan_slider, 30)
        return fan_slider

    def __create_fan_settings(self, device_id: str, channel: str) -> QVBoxLayout:
        """Create fan settings layout."""
        def update_value_on_import() -> None:
            """Update mode on Import."""
            mode_box.setCurrentText(self.__modes[device_id][channel])
            source_box.setCurrentText(self.__sources[device_id][channel])

        fan_settings: QVBoxLayout = QVBoxLayout()
        source_layout: QHBoxLayout = QHBoxLayout()
        source_layout.addWidget(utils.create_label("Source"))
        source_box: QComboBox = QComboBox()
        source_box.addItems([*self.__temps.get_data().keys()])
        source_box.currentTextChanged.connect(lambda source: self.__update_fan_source(device_id,
                                                                                      channel,
                                                                                      source))
        current_text: str = source_box.currentText()
        if device_id in self.__sources:
            current_text = self.__sources[device_id][channel]
            source_box.setCurrentText(current_text)
        source_layout.addWidget(source_box)
        self.__update_fan_source(device_id, channel, current_text)
        mode_layout: QHBoxLayout = QHBoxLayout()
        mode_layout.addWidget(utils.create_label("Mode"))
        mode_box: QComboBox = QComboBox()
        mode_box.addItems(["Normal", "Aggressive", "Silent", "Custom"])
        mode_box.currentTextChanged.connect(lambda mode: self.__update_fan_mode(device_id,
                                                                                channel,
                                                                                mode))
        current_text: str = mode_box.currentText()
        if device_id in self.__modes:
            current_text = self.__modes[device_id][channel]
            mode_box.setCurrentText(current_text)
        self.__update_fan_mode(device_id, channel, current_text)
        self.__update_signal.imported.connect(update_value_on_import)
        mode_layout.addWidget(mode_box)
        fan_settings.addLayout(source_layout)
        fan_settings.addLayout(mode_layout)
        return fan_settings

    def __create_fan_layout(self, device_id: str, channel: str) -> QVBoxLayout:
        """Create fan layout."""
        fan_layout: QVBoxLayout = QVBoxLayout()
        channel_label: QLabel = utils.create_label(channel, target="channel")
        fan_layout.addWidget(channel_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        slider_layout: QHBoxLayout = QHBoxLayout()
        slider_layout.addLayout(utils.create_ruler())
        fan_slider: QSlider = self.__create_fan_slider(device_id, channel)
        slider_layout.addWidget(fan_slider, alignment=Qt.AlignmentFlag.AlignHCenter)
        slider_layout.addLayout(utils.create_ruler(left=False))
        fan_layout.addLayout(slider_layout)
        fan_layout.addLayout(self.__create_fan_settings(device_id, channel))
        return fan_layout

    def __create_device_layout(self, device: Any, device_id: str) -> QVBoxLayout:
        """Create Device Layout."""
        device_layout: QVBoxLayout = QVBoxLayout()
        name_label: QLabel = utils.create_label(device.description, target="device")
        device_layout.addWidget(name_label, alignment=Qt.AlignmentFlag.AlignCenter)
        fans_layout: QHBoxLayout = QHBoxLayout()
        channels: list[str] = list(device._speed_channels.keys())
        for channel in channels:
            fans_layout.addLayout(self.__create_fan_layout(device_id, channel))
            if channel != channels[-1]:
                fans_layout.addWidget(utils.create_separator())
        device_layout.addLayout(fans_layout)
        return device_layout
