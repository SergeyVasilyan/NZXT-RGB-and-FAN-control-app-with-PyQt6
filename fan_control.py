#!/usr/bin/env python3
"""Own NZXT Fan Control GUI application."""

import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests
from liquidctl import find_liquidctl_devices
from PyQt6.QtCore import (
    QEvent,
    QObject,
    QRect,
    QRegularExpression,
    QSize,
    Qt,
    QThread,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QAction,
    QCloseEvent,
    QColor,
    QFont,
    QGuiApplication,
    QIcon,
    QPainter,
    QPalette,
    QPixmap,
    QRegularExpressionValidator,
    QWindowStateChangeEvent,
)
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
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
        self.__styles: str = "styles.qss"
        self.__load_stylesheet()

    def __load_stylesheet(self) -> None:
        """Load styles qss."""
        try:
            with open(self.__styles, "r") as f:
                self.setStyleSheet(f.read())
        except Exception as _:
            return

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

@dataclass
class ServerConfiguration:
    """Server Configuration."""

    ip: str = "192.168.10.17"
    port: int = 8085
    rate: float = 1.0

class SettingsDialog(QDialog):
    """Simple Settings selection Dialog."""

    def __init__(self, config: ServerConfiguration) -> None:
        """INIT."""
        super().__init__()
        self.setWindowTitle("Settings")
        self.setFixedSize(300, 150)
        self.__ip_input: QLineEdit
        self.__port_input: QLineEdit
        self.__rate_spin_box: QDoubleSpinBox
        self.__config: ServerConfiguration = config
        self.__create_layout()

    def __validate_inputs(self) -> None:
        """Validate IP and PORT."""
        ip_text: str = self.__ip_input.text()
        port_text: int = int(self.__port_input.text())
        if not self.__ip_input.hasAcceptableInput():
            QMessageBox.warning(self, "Invalid IP", "Please enter a valid IPv4 address.")
            return
        try:
            port: int = port_text
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Invalid Port",
                                "Port must be an integer between 1 and 65535.")
            return
        rate: float = round(self.__rate_spin_box.value(), 2)
        self.__config.ip = ip_text
        self.__config.port = port_text
        self.__config.rate = rate
        QMessageBox.information(self, "Success", f"IP: {ip_text}\nPort: {port_text}\nRate: {rate}")
        self.close()

    def __create_ip_section(self) -> QHBoxLayout:
        """Create IP section."""
        ip_layout: QHBoxLayout = QHBoxLayout()
        ip_layout.addWidget(QLabel("IP Address:"))
        self.__ip_input = QLineEdit()
        self.__ip_input.setText(self.__config.ip)
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
        self.__port_input.setText(str(self.__config.port))
        self.__port_input.setPlaceholderText("Enter Port (1–65535)")
        self.__port_input.setPlaceholderText("Enter IP address")
        port_regex: QRegularExpression = QRegularExpression(
            r"^(6553[0-5]|655[0-2]\d|65[0-4]\d{2}|6[0-4]\d{3}|[1-5]\d{4}|\d{1,4})$"
        )
        self.__port_input.setValidator(QRegularExpressionValidator(port_regex))
        port_layout.addWidget(self.__port_input)
        return port_layout

    def __create_rate_section(self) -> QHBoxLayout:
        """Create Rate section."""
        rate_layout: QHBoxLayout = QHBoxLayout()
        rate_layout.addWidget(QLabel("Rate (in seconds):"))
        self.__rate_spin_box = QDoubleSpinBox()
        self.__rate_spin_box.setRange(0.1, 10.0)
        self.__rate_spin_box.setSingleStep(0.1)
        self.__rate_spin_box.setValue(self.__config.rate)
        rate_layout.addWidget(self.__rate_spin_box)
        return rate_layout

    def __create_layout(self) -> None:
        """Create Dialog layout."""
        layout: QVBoxLayout = QVBoxLayout()
        layout.addLayout(self.__create_ip_section())
        layout.addLayout(self.__create_port_section())
        layout.addLayout(self.__create_rate_section())
        submit_btn: QPushButton = QPushButton("Save")
        submit_btn.clicked.connect(self.__validate_inputs)
        layout.addWidget(submit_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(layout)

class Worker(QThread):
    """Worker thread that poll sensors temperature from the server at given rate."""
    temps: pyqtSignal = pyqtSignal(float, float)

    def __init__(self, config: ServerConfiguration, min_temp: float=30.) -> None:
        """INIT."""
        super().__init__()
        self.__min_temp: float = min_temp
        self.__config: ServerConfiguration = config

    def __get_temp(self) -> tuple[float, float]:
        """Get CPU Core Average and GPU temperature from LibreHardwareMonitor server."""
        cpu_temp: float = self.__min_temp
        gpu_temp: float = self.__min_temp
        response: requests.Response|None = None
        for _ in range(0, 3):
            try:
                response = requests.get(f"http://{self.__config.ip}:{self.__config.port}/data.json")
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
            time.sleep(self.__config.rate)

class MainWindow(QMainWindow):
    """Main Window."""

    def __init__(self, app_name: str="") -> None:
        """INIT."""
        super().__init__()
        self.__app_name: str = app_name
        self.__settings: str = "settings.json"
        self.__modes: ObservableDict = ObservableDict()
        self.__sources: ObservableDict = ObservableDict()
        self.__server_config: ServerConfiguration = ServerConfiguration()
        self.__dark_theme: bool = True
        self.__start_minimized: bool = False
        self.__minimize_on_exit: bool = False
        self.__load_settings()
        screen_size: QRect = QGuiApplication.primaryScreen().availableGeometry()
        self.setWindowTitle(self.__app_name)
        self.setMinimumSize(QSize(screen_size.width() // 2, screen_size.height() // 2))
        self.__icons: str = "icons"
        self.setWindowIcon(self.__create_icon("icon"))
        self.__devices: list[Any] = self.__init_devices()
        self.__min_temp: int = 30
        self.__temps: ObservableDict = ObservableDict({
            "CPU": self.__min_temp,
            "GPU": self.__min_temp,
            "AVG": self.__min_temp,
            "MAX": self.__min_temp,
        })
        self.__worker: Worker = Worker(self.__server_config, min_temp=self.__min_temp)
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

    def __create_icon(self, name: str, dark: bool=True) -> QIcon:
        """Create themed QIcon."""
        if not name:
            return QIcon()
        pixmap: QPixmap = QPixmap(f"{self.__icons}/{name}.png")
        if pixmap.isNull():
            return QIcon()
        painter: QPainter = QPainter()
        if painter.begin(pixmap):
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            painter.fillRect(pixmap.rect(), QColor("white" if dark else "black"))
            painter.end()
        return QIcon(pixmap)

    def __force_refresh(self, widget: QWidget) -> None:
        """Force refresh widget style."""
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    def __create_label(self, text: str, size: str="", target: str="") -> QLabel:
        """Create QLabel with dynamic QSS."""
        size_map: dict[str, int] = {
            "small": 2,
            "medium": 4,
            "large": 6 ,
        }
        label: QLabel = QLabel(text)
        font: QFont = label.font()
        font.setPointSize((size_map.get(size, size_map["small"]) * self.height()) // 100)
        label.setFont(font)
        if target:
            label.setProperty("for", target)
        self.__force_refresh(label)
        return label

    def __create_system_tray(self) -> None:
        """Create and setup system tray icon."""
        self.__tray_icon = QSystemTrayIcon(self.__create_icon("icon"), self)
        self.__tray_icon.setToolTip(self.__app_name)
        self.__tray_icon.activated.connect(self.__on_tray_activated)
        tray_menu: QMenu = QMenu()
        self.__tray_icon.setContextMenu(tray_menu)
        restore_action: QAction = QAction(self.__create_icon("restore"), "Restore", self)
        quit_action: QAction = QAction(self.__create_icon("quit"), "Quit", self)
        restore_action.triggered.connect(self.__restore_window)
        quit_action.triggered.connect(self.__close)
        tray_menu.addAction(restore_action)
        tray_menu.addAction(quit_action)
        self.__tray_icon.show()

    def __create_file_menu(self, menu_bar: QMenuBar) -> None:
        """Create file menu section."""
        file_menu: QMenu = menu_bar.addMenu(self.__create_icon("file"), "&File")
        for action, trigger in [("export", self.__on_export_triggered),
                                ("import", self.__on_import_triggered)]:
            qaction: QAction = QAction(self.__create_icon(action),
                                             f"&{action.title()}",
                                             file_menu)
            qaction.triggered.connect(trigger)
            file_menu.addAction(qaction)

    def __create_settings_menu(self, menu_bar: QMenuBar) -> None:
        """Create settings menu."""
        def update_start_minimized() -> None:
            """Update start minimized setting."""
            self.__start_minimized = not self.__start_minimized
            start_icon = self.__create_icon("check" if self.__start_minimized else "")
            start_minimized.setIcon(start_icon)

        def update_minimize_on_exit() -> None:
            """Update minimize on exit setting."""
            self.__minimize_on_exit = not self.__minimize_on_exit
            minimize_icon = self.__create_icon("check" if self.__minimize_on_exit else "")
            minimize_on_exit.setIcon(minimize_icon)

        settings_menu: QMenu = menu_bar.addMenu(self.__create_icon("settings"), "&Settings")
        network_action: QAction = QAction(self.__create_icon("network"),
                                         "&Source configuration",
                                         settings_menu)
        start_icon: QIcon = self.__create_icon("check" if self.__start_minimized else "")
        start_minimized: QAction = QAction(start_icon, "Start minimized", settings_menu)
        minimize_icon: QIcon = self.__create_icon("check" if self.__minimize_on_exit else "")
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
        self.__dark_theme = settings.get("dark_theme", False)
        if server_config := settings.get("server", {}):
            self.__server_config.ip = server_config.get("ip", "")
            self.__server_config.port = server_config.get("port", -1)
            self.__server_config.rate = server_config.get("rate", 1)

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
            configuration["server"] = {
                "ip": self.__server_config.ip,
                "port": self.__server_config.port,
                "rate": self.__server_config.rate,
            }
            configuration["start_minimized"] = self.__start_minimized
            configuration["minimize_on_exit"] = self.__minimize_on_exit
            configuration["dark_theme"] = self.__dark_theme
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
        dialog: SettingsDialog = SettingsDialog(self.__server_config)
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

    @staticmethod
    def __create_separator(horizontal: bool=False) -> QFrame:
        separator: QFrame = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine if horizontal else QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setLineWidth(1)
        return separator

    def __create_temp_layout(self, source: str) -> QVBoxLayout:
        """Create Temp layout."""
        temp_layout: QVBoxLayout = QVBoxLayout()
        source_label: QLabel = self.__create_label(source, size="large", target="source")
        temp_layout.addWidget(source_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        temp_label: QLabel = self.__create_label(f"{self.__temps[source]} C", size="medium")
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

    def __create_fan_settings(self, device_id: str, channel: str) -> QVBoxLayout:
        """Create fan settings layout."""
        def update_value_on_import() -> None:
            """Update mode on Import."""
            mode_box.setCurrentText(self.__modes[device_id][channel])
            source_box.setCurrentText(self.__sources[device_id][channel])

        fan_settings: QVBoxLayout = QVBoxLayout()
        source_layout: QHBoxLayout = QHBoxLayout()
        source_layout.addWidget(self.__create_label("Source"))
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
        mode_layout.addWidget(self.__create_label("Mode"))
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
        channel_label: QLabel = self.__create_label(channel, target="channel")
        fan_layout.addWidget(channel_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        fan_slider: QSlider = self.__create_fan_slider(device_id, channel)
        fan_layout.addWidget(fan_slider, alignment=Qt.AlignmentFlag.AlignHCenter)
        fan_layout.addLayout(self.__create_fan_settings(device_id, channel))
        return fan_layout

    def __create_device_layout(self, device: Any, device_id: str) -> QVBoxLayout:
        """Create Device Layout."""
        device_layout: QVBoxLayout = QVBoxLayout()
        name_label: QLabel = self.__create_label(device.description, target="device")
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
        central_widget.setProperty("id", "central")
        self.__force_refresh(central_widget)
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
