#!/usr/bin/env python3
"""Own NZXT Fan Control GUI application."""

import os
import sys
import requests
import json
import time

from datetime import datetime
from typing import Any
from liquidctl import find_liquidctl_devices
from PyQt6.QtGui import (
    QAction,
    QCloseEvent,
    QColor,
    QFont,
    QGuiApplication,
    QIcon,
    QPalette,
    QRegularExpressionValidator,
    QWindowStateChangeEvent
)
from PyQt6.QtCore import (
    QEvent,
    QObject,
    QRegularExpression,
    QTimer,
    Qt,
    QSize,
    QRect,
    QThread,
    pyqtSignal
)
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QSlider,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)


class Application(QApplication):
    """Main Application."""

    def __init__(self) -> None:
        """INIT."""
        super().__init__([])

class ObservableDict(QObject):
    """Custom Dict with onChange signal."""
    value_changed: pyqtSignal = pyqtSignal(dict)

    def __init__(self, initial: dict|None=None):
        """INIT."""
        super().__init__()
        self.__data: dict[str, Any] = initial or {}

    def __getitem__(self, key: str) -> Any:
        """Get item from dict."""
        return self.__data.get(key, None)

    def __setitem__(self, key: str, value: Any) -> None:
        """Set value under given key in dict."""
        self.update(key, value)

    def __contains__(self, key: str) -> bool:
        """Check if given key exists in dict."""
        return key in self.__data

    def __repr__(self) -> str:
        """Print dict representation."""
        return repr(self.__data)

    def update(self, key: str, value: Any) -> None:
        """Update dict value under given key."""
        self.__data[key] = value
        self.value_changed.emit(self.__data.copy())

    def get_data(self) -> dict[str, Any]:
        """Get whole dict."""
        return self.__data.copy()

class ImportSignal(QObject):
    """Simple import update signal."""
    imported: pyqtSignal = pyqtSignal()

    def __init__(self) -> None:
        """INIT."""
        super().__init__()

    def update(self) -> None:
        """Trigger signal."""
        self.imported.emit()

class ServerConfiguration:
    """Server Configuration."""

    def __init__(self, ip: str="192.168.10.17", port: int=8085) -> None:
        """INIT."""
        super().__init__()
        self.__ip: str = ip
        self.__port: int = port

    def get(self) -> tuple[str, int]:
        """Trigger signal."""
        return self.__ip, self.__port

    def set(self, ip: str, port: int) -> None:
        """Trigger signal."""
        if ip:
            self.__ip = ip
        if -1 != port:
            self.__port = port

class IPPortDialog(QDialog):
    """Simple IP and PORT selection Dialog."""

    def __init__(self, config: ServerConfiguration) -> None:
        """INIT."""
        super().__init__()
        self.setWindowTitle("IP and Port Input")
        self.setFixedSize(300, 150)
        self.__ip_input: QLineEdit
        self.__port_input: QLineEdit
        self.__config: ServerConfiguration = config
        self.__create_layout()

    def __validate_inputs(self) -> None:
        """Validate IP and PORT."""
        ip: str = self.__ip_input.text()
        port_text: str = self.__port_input.text()
        if not self.__ip_input.hasAcceptableInput():
            QMessageBox.warning(self, "Invalid IP", "Please enter a valid IPv4 address.")
            return
        try:
            port: int = int(port_text)
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Invalid Port", "Port must be an integer between 1 and 65535.")
            return
        self.__config.set(ip, port)
        QMessageBox.information(self, "Success", f"IP: {ip}\nPort: {port}")
        self.close()

    def __create_ip_section(self) -> QHBoxLayout:
        """Create IP section."""
        ip_layout: QHBoxLayout = QHBoxLayout()
        ip_layout.addWidget(QLabel("IP Address:"))
        self.__ip_input = QLineEdit()
        self.__ip_input.setText(self.__config.get()[0])
        self.__ip_input.setPlaceholderText("Enter IP address")
        ip_regex: QRegularExpression = QRegularExpression(
            r"^(25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)"
            r"(\.(25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)){3}$"
        )
        self.__ip_input.setValidator(QRegularExpressionValidator(ip_regex))
        ip_layout.addWidget(self.__ip_input)
        return ip_layout

    def __create_port_section(self) -> QHBoxLayout:
        """Create PORT section."""
        port_layout: QHBoxLayout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.__port_input = QLineEdit()
        self.__port_input.setText(str(self.__config.get()[1]))
        self.__port_input.setPlaceholderText("Enter Port (1–65535)")
        port_layout.addWidget(self.__port_input)
        return port_layout

    def __create_layout(self) -> None:
        """Create Dialog layout."""
        layout: QVBoxLayout = QVBoxLayout()
        layout.addLayout(self.__create_ip_section())
        layout.addLayout(self.__create_port_section())
        submit_btn: QPushButton = QPushButton("Save")
        submit_btn.clicked.connect(self.__validate_inputs)
        layout.addWidget(submit_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(layout)

class Worker(QThread):
    temps: pyqtSignal = pyqtSignal(float, float)

    def __init__(self, config: ServerConfiguration, interval: float=1.0, min_temp: float=30.) -> None:
        """INIT."""
        super().__init__()
        self.__interval: float = interval
        self.__min_temp: float = min_temp
        self.__config: ServerConfiguration = config

    def __get_temp(self) -> tuple[float, float]:
        """Get CPU Core Average and GPU temperature from LibreHardwareMonitor server."""
        cpu_temp: float = self.__min_temp
        gpu_temp: float = self.__min_temp
        response: requests.Response|None = None
        ip, port = self.__config.get()
        for _ in range(0, 3):
            try:
                response = requests.get(f"http://{ip}:{port}/data.json")
            except requests.exceptions.ConnectionError:
                time.sleep(1)
        if response and response.ok:
            data: dict[str, Any] = response.json()
            is_cpu_set: bool = False
            is_gpu_set: bool = False
            for hw in data.get("Children", [{}])[0].get("Children", []):
                if is_cpu_set and is_gpu_set:
                    break
                if not is_cpu_set and "12th Gen Intel Core i9-12900K" in hw["Text"]:
                    for sensor in hw["Children"]:
                        if "Temperatures" in sensor["Text"]:
                            for temp_sensor in sensor["Children"]:
                                if "Core Average" in temp_sensor["Text"]:
                                    cpu_temp = float(temp_sensor["Value"].replace(" °C", ""))
                                    is_cpu_set = True
                if not is_gpu_set and "NVIDIA GeForce RTX 4070 SUPER" in hw["Text"]:
                    for sensor in hw["Children"]:
                        if "Temperatures" in sensor["Text"]:
                            for temp_sensor in sensor["Children"]:
                                if "GPU Core" in temp_sensor["Text"]:
                                    gpu_temp = float(temp_sensor["Value"].replace(" °C", ""))
                                    is_gpu_set = True
        return cpu_temp, gpu_temp

    def run(self):
        """Get CPU Core Average and GPU temperature from LibreHardwareMonitor server."""
        while True:
            self.temps.emit(*self.__get_temp())
            time.sleep(self.__interval)

class MainWindow(QMainWindow):
    """Main Window."""

    def __init__(self, app_name: str="") -> None:
        """INIT."""
        super().__init__()
        self.__app_name: str = app_name
        self.__icons: str = "icons"
        self.__settings: str = "settings.json"
        self.__modes: ObservableDict = ObservableDict()
        self.__sources: ObservableDict = ObservableDict()
        self.__server_config: ServerConfiguration = ServerConfiguration()
        self.__start_minimized: bool = False
        self.__minimize_on_exit: bool = False
        self.__load_settings()
        screen_size: QRect = QGuiApplication.primaryScreen().availableGeometry()
        self.setWindowTitle(self.__app_name)
        self.setMinimumSize(QSize(screen_size.width() // 2, screen_size.height() // 2))
        self.setWindowIcon(QIcon(f"{self.__icons}/icon.png"))
        self.__devices: list[Any] = self.__init_devices()
        self.__min_temp: int = 30
        self.__temps: ObservableDict = ObservableDict({
            "CPU": self.__min_temp,
            "GPU": self.__min_temp,
            "AVG": self.__min_temp,
            "MAX": self.__min_temp,
        })
        self.__worker: Worker = Worker(self.__server_config, interval=1.0, min_temp=self.__min_temp)
        self.__worker.temps.connect(self.__update_temps)
        self.__worker.start()
        self.__update_signal: ImportSignal = ImportSignal()
        self.__tray_icon: QSystemTrayIcon
        self.__create_system_tray()
        self.__create_menubar()
        self.__create_central_widget()
        if self.__start_minimized:
            QTimer.singleShot(0, self.hide)
        else:
            self.show()

    def __create_system_tray(self) -> None:
        """Create and setup system tray icon."""
        self.__tray_icon = QSystemTrayIcon(QIcon(f"{self.__icons}/icon.png"), self)
        self.__tray_icon.setToolTip(self.__app_name)
        self.__tray_icon.activated.connect(self.__on_tray_activated)
        tray_menu: QMenu = QMenu()
        self.__tray_icon.setContextMenu(tray_menu)
        restore_action: QAction = QAction(QIcon(f"{self.__icons}/restore.png"), "Restore", self)
        quit_action: QAction = QAction(QIcon(f"{self.__icons}/exit.png"), "Quit", self)
        restore_action.triggered.connect(self.__restore_window)
        quit_action.triggered.connect(self.__close)
        tray_menu.addAction(restore_action)
        tray_menu.addAction(quit_action)
        self.__tray_icon.show()

    def __create_file_menu(self, menu_bar: QMenuBar) -> None:
        """Create file menu section."""
        file_menu: QMenu = menu_bar.addMenu(QIcon(f"{self.__icons}/file.png"), "&File")
        for action, trigger in [("export", self.__on_export_triggered), ("import", self.__on_import_triggered)]:
            qaction: QAction = QAction(QIcon(f"{self.__icons}/{action}.png"),
                                             f"&{action.title()}",
                                             file_menu)
            qaction.triggered.connect(trigger)
            file_menu.addAction(qaction)

    def __create_settings_menu(self, menu_bar: QMenuBar) -> None:
        """Create settings menu."""
        def update_start_minimized() -> None:
            """Update start minimized setting."""
            self.__start_minimized = not self.__start_minimized
            start_icon = QIcon(f"{self.__icons}/check.png" if self.__start_minimized else "")
            start_minimized.setIcon(start_icon)

        def update_minimize_on_exit() -> None:
            """Update minimize on exit setting."""
            self.__minimize_on_exit = not self.__minimize_on_exit
            minimize_icon = QIcon(f"{self.__icons}/check.png" if self.__minimize_on_exit else "")
            minimize_on_exit.setIcon(minimize_icon)

        settings_menu: QMenu = menu_bar.addMenu(QIcon(f"{self.__icons}/settings.png"), "&Settings")
        network_action: QAction = QAction(QIcon(f"{self.__icons}/network.png"),
                                         "&Source configuration",
                                         settings_menu)
        start_icon: QIcon = QIcon(f"{self.__icons}/check.png" if self.__start_minimized else "")
        start_minimized: QAction = QAction(start_icon, "Start minimized", settings_menu)
        minimize_icon: QIcon = QIcon(f"{self.__icons}/check.png" if self.__minimize_on_exit else "")
        minimize_on_exit: QAction = QAction(minimize_icon, "Minimized on exit", settings_menu)
        network_action.triggered.connect(self.__on_network_triggered)
        start_minimized.triggered.connect(update_start_minimized)
        minimize_on_exit.triggered.connect(update_minimize_on_exit)
        settings_menu.addAction(network_action)
        settings_menu.addAction(start_minimized)
        settings_menu.addAction(minimize_on_exit)

    def __create_menubar(self) -> None:
        """Create and configure menubar."""
        menu_bar: QMenuBar = QMenuBar(self)
        self.__create_file_menu(menu_bar)
        self.__create_settings_menu(menu_bar)
        self.setMenuBar(menu_bar)

    def __export_current_configuration(self) -> dict[str, Any]:
        """Export current configuration."""
        devices: dict[str, Any] = {}
        modes: dict[str, Any] = self.__modes.get_data()
        sources: dict[str, Any] = self.__sources.get_data()
        for device_id, fans in modes.items():
            devices[device_id] = {}
            for fan_id, mode in fans.items():
                devices[device_id][fan_id] = {
                    "mode": mode,
                    "source": sources[device_id][fan_id],
                }
        configuration: dict[str, Any] = {
            "date": str(datetime.now()),
            "devices": devices,
        }
        return configuration

    def __load_configuration(self, configuration: dict[str, Any]) -> None:
        """Load configuration."""
        for device_id, fans in configuration.items():
            configuration[device_id] = {}
            device_modes: dict[str, Any] = {}
            device_sources: dict[str, Any] = {}
            for fan_id, fan_info in fans.items():
                device_modes[fan_id] = fan_info["mode"]
                device_sources[fan_id] = fan_info["source"]
            self.__modes[device_id] = device_modes
            self.__sources[device_id] = device_sources

    def __load_settings(self) -> None:
        """Load current settings."""
        if not os.path.exists(self.__settings):
            return
        settings: dict[str, Any] = {}
        with open(self.__settings, "r") as f:
            settings = json.load(f)
        self.__load_configuration(settings.get("devices", {}))
        self.__start_minimized = settings.get("start_minimized", False)
        self.__minimize_on_exit = settings.get("minimize_on_exit", False)
        if server_config := settings.get("server", {}):
            self.__server_config.set(server_config.get("ip", ""), server_config.get("port", -1))

    def __close(self) -> None:
        """Close app normally."""
        reply: QMessageBox.StandardButton = QMessageBox.question(self, "Exit",
                                                                 "Are you sure you want to quit?",
                                                                 QMessageBox.StandardButton.Yes |
                                                                 QMessageBox.StandardButton.No,
                                                                 QMessageBox.StandardButton.No)

        if QMessageBox.StandardButton.Yes == reply:
            for device in self.__devices:
                device.disconnect()
            configuration: dict[str, Any] = self.__export_current_configuration()
            ip, port = self.__server_config.get()
            configuration["server"] = {
                "ip": ip,
                "port": port,
            }
            configuration["start_minimized"] = self.__start_minimized
            configuration["minimize_on_exit"] = self.__minimize_on_exit
            with open(self.__settings, "w") as f:
                json.dump(configuration, f, indent=4)
            QApplication.quit()

    def __restore_window(self) -> None:
        """Restore app window."""
        self.showNormal()
        self.activateWindow()

    def __on_tray_activated(self, reason: QEvent):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.__restore_window()

    def __on_export_triggered(self, _event: QEvent) -> None:
        """On Export action triggered."""
        filename, _ = QFileDialog.getSaveFileName(self, "Export Configuration",
                                                  "export_configuration", "JSON (*.json)")
        if not filename:
            return
        message: str = "Current configuration successfully exported."
        icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information
        try:
            with open(filename, "w") as f:
                json.dump(self.__export_current_configuration(), f, indent=4)
        except Exception as _:
            message = "Failed to export configuration.\nPlease choose another location."
            icon = QSystemTrayIcon.MessageIcon.Critical
        self.__tray_icon.showMessage("Export Configuration", message, icon, 3000)

    def __on_import_triggered(self, _event: QEvent) -> None:
        """On Import action triggered."""
        configuration: dict[str, Any] = {}
        filename, _ = QFileDialog.getOpenFileName(self, "Select a Configuration", "",
                                                  "JSON (*.json)")
        if not filename:
            return
        message: str = "Current configuration successfully exported."
        icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information
        try:
            with open(filename, "r") as f:
                configuration = json.load(f)
        except Exception as _:
            message = "Failed to import configuration.\nPlease choose valid file."
            icon = QSystemTrayIcon.MessageIcon.Critical
        self.__load_configuration(configuration.get("devices", {}))
        self.__update_signal.update()
        self.__tray_icon.showMessage("Import Configuration", message, icon, 3000)

    def __on_network_triggered(self, _event: QEvent) -> None:
        """On Source Configuration triggered."""
        dialog: IPPortDialog = IPPortDialog(self.__server_config)
        dialog.exec()

    def __update_temps(self, cpu: float, gpu: float) -> None:
        """Update CPU and GPU temperatures."""
        self.__temps["CPU"] = cpu
        self.__temps["GPU"] = gpu
        self.__temps["AVG"] = (cpu + gpu) / 2
        self.__temps["MAX"] = max(cpu, gpu)

    @staticmethod
    def __update_temp_label(label: QLabel, new_temps: dict[str, float], source: str) -> None:
        """Update temperature label."""
        new_temp: float = new_temps.get(source, 0)
        label.setText(f"{new_temp} C")
        label.setStyleSheet(f"color: hsl({100 - new_temp}, 100%, 50%);")

    @staticmethod
    def __update_slider_style(slider: QSlider, value: int) -> None:
        """Update given QSlider style."""
        isEnabled: bool = slider.isEnabled()
        cursor: Qt.CursorShape = Qt.CursorShape.ClosedHandCursor
        if not isEnabled:
           cursor = Qt.CursorShape.ForbiddenCursor
        slider.setCursor(cursor)
        lightness: int = 50 if isEnabled else 30
        slider.setStyleSheet(f"""
            QSlider::groove:vertical {{
                background: hsl(0, 0%, 0%);
                border-radius: 5px;
                width: 10px;
                margin: 0px;
            }}
            QSlider::handle:vertical {{
                background: hsl(200, 100%, {lightness}%);
                border: none;
                border-radius: 10px;
                margin: 0 -6px;
                height: 20px;
                width: 20px;
            }}
            QSlider::sub-page:vertical {{
                background: hsl(0, 0%, 0%);
            }}
            QSlider::add-page:vertical {{
                background: hsl({100 - value}, 100%, {lightness}%);
            }}
        """)

    def __update_fan_speed(self, device_id: str, channel: str, value: int, fan_slider: QSlider) -> None:
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
    def __get_channel_mode(new_modes: dict[str, Any]|ObservableDict, device_id: str, channel: str) -> str:
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

    @staticmethod
    def __create_separator(horizontal: bool=False) -> QFrame:
        separator: QFrame = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine if horizontal else QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setLineWidth(1)
        return separator

    def __create_label(self, text: str, ratio: int, bold: bool=False) -> QLabel:
        """Create QLabel with custom font and size."""
        label: QLabel = QLabel(text)
        font_size: int = max(10, (self.width() * ratio) // 100)
        font: QFont = QFont("Arial", font_size)
        font.setBold(bold)
        label.setFont(font)
        return label

    def __create_temp_layout(self, source: str) -> QVBoxLayout:
        """Create Temp layout."""
        temp_layout: QVBoxLayout = QVBoxLayout()
        source_label: QLabel = self.__create_label(source, 3, bold=True)
        source_label.setStyleSheet("color: hsl(196, 100%, 50%);")
        temp_layout.addWidget(source_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        temp_label: QLabel = self.__create_label(f"{self.__temps[source]} C", 2)
        self.__temps.value_changed.connect(lambda new_temps: self.__update_temp_label(temp_label,
                                                                                      new_temps,
                                                                                      source))
        temp_layout.addWidget(temp_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        temp_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        return temp_layout

    def __create_temps_layout(self) -> QHBoxLayout:
        """Create CPU and GPU temperatures layout."""
        temps_layout: QHBoxLayout = QHBoxLayout()
        sources: list[str] = ["CPU", "GPU"]
        for source in sources:
            temps_layout.addLayout(self.__create_temp_layout(source))
            if source != sources[-1]:
                temps_layout.addWidget(self.__create_separator())
        return temps_layout


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

    def __create_fan_title(self, device_id: str, channel: str) -> QHBoxLayout:
        """Create Fan title with combobox."""
        def update_value_on_import() -> None:
            """Update mode on Import."""
            source_box.setCurrentText(self.__sources[device_id][channel])

        fan_header_layout: QHBoxLayout = QHBoxLayout()
        channel_label: QLabel = self.__create_label(channel, 1)
        channel_label.setStyleSheet("color: hsl(200, 100%, 50%);")
        fan_header_layout.addWidget(channel_label)
        source_box: QComboBox = QComboBox()
        source_box.addItems([*self.__temps.get_data().keys()])
        source_box.currentTextChanged.connect(lambda source: self.__update_fan_source(device_id,
                                                                                      channel,
                                                                                      source))
        current_text: str = source_box.currentText()
        if device_id in self.__sources:
            current_text = self.__sources[device_id][channel]
            source_box.setCurrentText(current_text)
        self.__update_fan_source(device_id, channel, current_text)
        self.__update_signal.imported.connect(update_value_on_import)
        fan_header_layout.addWidget(source_box)
        return fan_header_layout

    def __create_fan_layout(self, device_id: str, channel: str) -> QVBoxLayout:
        """Create fan layout."""
        def update_value_on_import() -> None:
            """Update mode on Import."""
            mode_box.setCurrentText(self.__modes[device_id][channel])

        fan_layout: QVBoxLayout = QVBoxLayout()
        fan_layout.addLayout(self.__create_fan_title(device_id, channel))
        fan_slider: QSlider = self.__create_fan_slider(device_id, channel)
        fan_layout.addWidget(fan_slider, alignment=Qt.AlignmentFlag.AlignHCenter)
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
        fan_layout.addWidget(mode_box, alignment=Qt.AlignmentFlag.AlignHCenter)
        return fan_layout

    def __create_device_layout(self, device: Any, device_id: str) -> QVBoxLayout:
        """Create Device Layout."""
        device_layout: QVBoxLayout = QVBoxLayout()
        name_label: QLabel = self.__create_label(device.description, 1, bold=True)
        name_label.setStyleSheet("color: hsl(284, 100%, 50%);")
        device_layout.addWidget(name_label, alignment=Qt.AlignmentFlag.AlignCenter)
        fans_layout: QHBoxLayout = QHBoxLayout()
        channels: list[str] = list(device._speed_channels.keys())
        for channel in channels:
            fans_layout.addLayout(self.__create_fan_layout(device_id, channel))
            if channel != channels[-1]:
                fans_layout.addWidget(self.__create_separator())
        device_layout.addLayout(fans_layout)
        return device_layout

    def __create_devices_layout(self) -> QHBoxLayout:
        """Create Devices layout."""
        devices_layout: QHBoxLayout = QHBoxLayout()
        for device_id, device in enumerate(self.__devices):
            devices_layout.addLayout(self.__create_device_layout(device, str(device_id)))
            if device != self.__devices[-1]:
                devices_layout.addWidget(self.__create_separator())
        return devices_layout

    def __configure_layouts(self, central_widget: QWidget) -> None:
        """Create and configure layouts."""
        main_layout: QVBoxLayout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        main_layout.addLayout(self.__create_temps_layout())
        main_layout.addWidget(self.__create_separator(horizontal=True))
        main_layout.addLayout(self.__create_devices_layout())

    def __create_central_widget(self) -> None:
        """Create central widget."""
        central_widget: QWidget = QWidget()
        central_widget.setAutoFillBackground(True)
        palette: QPalette = central_widget.palette()
        background_color: QColor = QColor()
        background_color.setHsl(0, 0, 50)
        palette.setColor(central_widget.backgroundRole(), background_color)
        central_widget.setPalette(palette)
        self.__configure_layouts(central_widget)
        self.setCentralWidget(central_widget)

    def __init_devices(self) -> list[Any]:
        devices: list[Any] = []
        for device in find_liquidctl_devices():
            device.connect()
            if "NZXT" not in device.description:
                continue
            devices.append(device)
        return devices

    def closeEvent(self, event: QCloseEvent):
        """Override the close event to handle application minimize to system tray."""
        event.ignore()
        if not self.__minimize_on_exit:
            self.__close()
            return
        QTimer.singleShot(0, self.hide)
        self.__tray_icon.showMessage(
            "Minimized to Tray",
            "Your app is still running in the background.",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )

    def changeEvent(self, event: QWindowStateChangeEvent):
        """Override the change event to handle application minimize to system tray."""
        if event.type() == QEvent.Type.WindowStateChange\
            and self.windowState() & Qt.WindowState.WindowMinimized:
            QTimer.singleShot(0, self.hide)
            self.__tray_icon.showMessage(
                "Minimized to Tray",
                "App is still running in the background.",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )
        super().changeEvent(event)

    def connect_devices(self) -> bool:
        """Connect all devices."""
        try:
            for device in self.__devices:
                device.initialize()
            return True
        except Exception:
            return False

def main() -> int:
    """Start point."""
    app_name: str = "Finally NZXT Fan control"
    app: Application = Application()
    app.setApplicationName(app_name)
    window: MainWindow = MainWindow(app_name=app_name)
    window.connect_devices()
    app.exec()
    return 0

if "__main__" == __name__:
    sys.exit(main())
