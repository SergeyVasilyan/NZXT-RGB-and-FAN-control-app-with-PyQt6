#!/usr/bin/env python3
"""Own NZXT Fan Control GUI application."""

import json
import os
import re
import sys
import time
import socket
from dataclasses import dataclass
from datetime import datetime
from typing import Any, override

from liquidctl.driver.smart_device import SmartDevice2
import requests
import src.utils.common as utils
from PySide6.QtCore import (
    QEvent,
    QRect,
    QSize,
    Qt,
    QThread,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QGuiApplication,
    QIcon,
)
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QListWidget,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)
from src.layouts.device import DeviceSection
from src.layouts.temp import TemperatureSection
from src.utils.device_manager import DeviceManager
from src.utils.observable_dict import ObservableDict
from src.utils.signals import GLOBAL_SIGNALS
from src.widgets.application import Application
from src.widgets.config import AppConfig
from src.widgets.curve import FanCurve, FanCurvePoint
from src.widgets.menubar import MenuBar
from src.widgets.settings_dialog import ServerConfiguration
from src.widgets.theme_manager import ThemeManager


@dataclass
class DeviceInfo:
    """Device information class."""

    name: str
    pattern: str
    temp: float
    model: str = "N/A"

class Worker(QThread):
    """Worker thread that poll sensors temperature from the server at given rate."""
    new_info: Signal = Signal(DeviceInfo, DeviceInfo)

    def __init__(self, config: ServerConfiguration, temp_source: dict[str, str],
                       min_temp: float=30.) -> None:
        """INIT."""
        super().__init__()
        self.__run: bool = True
        self.__min_temp: float = min_temp
        self.__config: ServerConfiguration = config
        self.__temp_source: dict[str, str] = temp_source
        s: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        self.__local_ip: str = s.getsockname()[0]
        self.__config.ip = self.__local_ip
        self.__cpu: DeviceInfo = DeviceInfo(name="CPU", temp=self.__min_temp, pattern="(Intel|AMD)")
        self.__gpu: DeviceInfo = DeviceInfo(name="GPU", temp=self.__min_temp, pattern="(NVIDIA)")

    def __get_info_from_server(self) -> dict[str, Any]:
        """Get sensors information from the server."""
        response: requests.Response|None = None
        for _ in range(3):
            try:
                response = requests.get(f"http://{self.__config.ip}:{self.__config.port}/data.json")
            except requests.exceptions.ConnectionError:
                self.sleep(1)
        if response and response.ok:
            return response.json()
        return {}

    def __parse_info(self, hardware: dict[str, Any], is_cpu: bool=True) -> bool:
        """Parse sensor information."""
        device: DeviceInfo = self.__cpu if is_cpu else self.__gpu
        if re.search(device.pattern, hardware["Text"]):
            for sensor in hardware["Children"]:
                if "Temperatures" in sensor["Text"]:
                    for temp_sensor in sensor["Children"]:
                        if self.__temp_source[device.name] in temp_sensor["Text"]:
                            device.model = hardware["Text"]
                            device.temp = float(temp_sensor["Value"].replace(" °C", ""))
                            return True
        return False

    def __update_temp(self) -> None:
        """Get CPU Core Average and GPU temperature from LibreHardwareMonitor server."""
        is_cpu_set: bool = False
        is_gpu_set: bool = False
        data: dict[str, Any] = self.__get_info_from_server()
        for hw in data.get("Children", [{}])[0].get("Children", []):
            if is_cpu_set and is_gpu_set:
                break
            if not is_cpu_set:
                is_cpu_set = self.__parse_info(hw)
            if not is_gpu_set:
                is_gpu_set = self.__parse_info(hw, is_cpu=False)

    @override
    def quit(self) -> None:
        """Override quit slot."""
        self.__run = False
        self.exit(0)

    @override
    def run(self):
        """Get CPU Core Average and GPU temperature from LibreHardwareMonitor server."""
        while self.__run:
            self.__update_temp()
            self.new_info.emit(self.__cpu, self.__gpu)
            self.msleep(self.__config.rate)

class MainWindow(QMainWindow):
    """Main Window."""

    def __init__(self, app_name: str, theme_manager: ThemeManager) -> None:
        """INIT."""
        super().__init__()
        self.__app_name: str = app_name
        self.__settings: str = "settings.json"
        AppConfig.set("theme", "dark")
        AppConfig.set("start_minimized", False)
        AppConfig.set("minimize_on_exit", False)
        self.__theme_manager: ThemeManager = theme_manager
        self.__sources: ObservableDict = ObservableDict()
        self.__curves: dict[str, dict[str, list[FanCurvePoint]]] = {}
        self.__server_config: ServerConfiguration = ServerConfiguration()
        screen_size: QRect = QGuiApplication.primaryScreen().availableGeometry()
        self.setWindowTitle(self.__app_name)
        self.setMinimumSize(QSize(screen_size.width() // 2, screen_size.height() // 2))
        self.setWindowIcon(self.__create_icon("icon"))
        self.__min_temp: int = 30
        self.__temps: ObservableDict = ObservableDict({
            "CPU": self.__min_temp,
            "GPU": self.__min_temp,
            "AVG": self.__min_temp,
            "MAX": self.__min_temp,
        })
        self.__names: ObservableDict = ObservableDict({
            "CPU": "N/A",
            "GPU": "N/A",
        })
        self.__temp_source: dict[str, str] = {
            "CPU": "Core Average",
            "GPU": "GPU Core",
        }
        self.__load_settings()
        self.__theme_manager.apply_theme(AppConfig.get("theme"))
        self.__worker: Worker = Worker(self.__server_config, self.__temp_source, self.__min_temp)
        self.__worker.new_info.connect(self.__update_device_info)
        self.__worker.start()
        self.__tray_icon: QSystemTrayIcon
        self.__device_manager: DeviceManager = DeviceManager(self.__server_config)
        self.__create_system_tray()
        self.setMenuBar(MenuBar(self.__server_config, self.__export_current_configuration,
                                self.__load_configuration, self.__theme_manager, self.__tray_icon))
        self.__create_central_widget()
        if AppConfig.get("start_minimized", value_type=bool):
            QTimer.singleShot(0, self.hide)
        else:
            self.show()

    def __create_icon(self, name: str) -> QIcon:
        """Create themed QIcon."""
        return utils.create_icon(name, AppConfig.get("theme"))

    def __export_current_configuration(self, /, *, filename: str="",
                                             settings: bool=False) -> dict[str, Any]:
        """Export current configuration."""
        devices: dict[str, Any] = {}
        sources: dict[str, Any] = self.__sources.get_data()
        for device_id, channels in sources.items():
            devices[device_id] = {}
            for channel, source in channels.items():
                points: list[FanCurvePoint] = self.__curves.get(device_id, {}).get(channel, [])
                devices[device_id][channel] = {
                    "curve": FanCurve.convert_points_to_str(points),
                    "source": source,
                }
        configuration: dict[str, Any] = {
            "devices": devices,
        }
        if settings:
            filename = self.__settings
            configuration["sources"] = self.__temp_source
            configuration["server"] = {
                "ip": self.__server_config.ip,
                "port": self.__server_config.port,
                "rate": self.__server_config.rate,
            }
            for config in ["start_minimized", "minimize_on_exit", "start_at_logon", "theme"]:
                configuration[config] = AppConfig.get(config,
                                                      value_type=str if config == "theme" else bool)
        configuration["date"] = str(datetime.now())
        if filename:
            with open(filename, "w") as f:
                json.dump(configuration, f, indent=4)
        return configuration

    def __load_configuration(self, filename: str) -> None:
        """Load configuration."""
        configuration: dict[str, Any] = {}
        message: str = "Current configuration successfully imported."
        icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information
        try:
            with open(filename, "r") as f:
                configuration = json.load(f)
        except Exception as _:
            message = f"Failed to import '{filename}' configuration.\nPlease choose valid file."
            icon = QSystemTrayIcon.MessageIcon.Critical
        for device_id, channels in configuration.get("devices", {}).items():
            configuration[device_id] = {}
            sources: dict[str, Any] = {}
            curves: dict[str, list[FanCurvePoint]] = {}
            for channel, channel_info in channels.items():
                sources[channel] = channel_info["source"]
                curves[channel] = FanCurve.convert_str_to_points(channel_info["curve"])
            self.__sources[device_id] = sources
            self.__curves[device_id] = curves
        if filename != self.__settings:
            GLOBAL_SIGNALS.imported.emit()
            self.__tray_icon.showMessage("Import Configuration", message, icon, 3000)

    def __load_settings(self) -> None:
        """Load current settings."""
        if not os.path.exists(self.__settings):
            return
        self.__load_configuration(self.__settings)
        settings: dict[str, Any] = {}
        with open(self.__settings, "r") as f:
            settings = json.load(f)
        AppConfig.set("start_minimized", settings.get("start_minimized", False))
        AppConfig.set("minimize_on_exit", settings.get("minimize_on_exit", False))
        AppConfig.set("start_at_logon", settings.get("start_at_logon", False))
        AppConfig.set("theme", settings.get("theme", "dark"))
        if server_config := settings.get("server", {}):
            self.__server_config.ip = server_config.get("ip", "")
            self.__server_config.port = server_config.get("port", -1)
            self.__server_config.rate = server_config.get("rate", 1)
        if temp_source := settings.get("sources", {}):
            self.__temp_source = temp_source

    def __close(self) -> None:
        """Close app normally."""
        reply: QMessageBox.StandardButton = QMessageBox.question(self, "Exit",
                                                                 "Are you sure you want to quit?",
                                                                 QMessageBox.StandardButton.Yes |
                                                                 QMessageBox.StandardButton.No,
                                                                 QMessageBox.StandardButton.No)

        if QMessageBox.StandardButton.Yes == reply:
            self.__export_current_configuration(settings=True)
            self.__worker.quit()
            while self.__worker.isRunning():
                time.sleep(1)
            QApplication.quit()

    def __restore_window(self) -> None:
        """Restore app window."""
        self.showNormal()
        self.activateWindow()

    def __on_tray_activated(self, reason: QEvent) -> None:
        if reason in [QSystemTrayIcon.ActivationReason.DoubleClick,
                      QSystemTrayIcon.ActivationReason.Trigger]:
            self.__restore_window()

    def __update_device_info(self, cpu: DeviceInfo, gpu: DeviceInfo) -> None:
        """Update device information."""
        cpu_temp: float = cpu.temp
        gpu_temp: float = gpu.temp
        self.__temps["CPU"] = cpu_temp
        self.__temps["GPU"] = gpu_temp
        self.__temps["AVG"] = (cpu_temp + gpu_temp) / 2
        self.__temps["MAX"] = max(cpu_temp, gpu_temp)
        self.__names["CPU"] = cpu.model
        self.__names["GPU"] = gpu.model

    def __create_system_tray(self) -> None:
        """Create and setup system tray icon."""
        self.__tray_icon = QSystemTrayIcon(self.__create_icon("icon"), self)
        self.__tray_icon.setToolTip(self.__app_name)
        self.__tray_icon.activated.connect(self.__on_tray_activated)
        tray_menu: QMenu = QMenu()
        self.__tray_icon.setContextMenu(tray_menu)
        restore_action: QAction = QAction(self.__create_icon("restore"), "Restore", self)
        quit_action: QAction = QAction(self.__create_icon("exit"), "Exit", self)
        restore_action.triggered.connect(self.__restore_window)
        quit_action.triggered.connect(self.__close)
        tray_menu.addAction(restore_action)
        tray_menu.addAction(quit_action)
        self.__tray_icon.show()

    def __configure_layouts(self, central_widget: QWidget) -> None:
        """Create and configure layouts."""
        main_layout: QHBoxLayout = QHBoxLayout()
        left_layout: QVBoxLayout = QVBoxLayout()
        right_layout: QVBoxLayout = QVBoxLayout()
        list_widget: QListWidget = QListWidget()
        devices: list[SmartDevice2] = self.__device_manager.devices
        list_widget.addItems([device.description for device in devices])
        device_widget: DeviceSection = DeviceSection(devices, self.__sources, self.__temps,
                                                     self.__curves)
        self.__curves = device_widget.curves
        list_widget.currentRowChanged.connect(device_widget.update_layout)
        list_widget.setCurrentRow(0)
        main_layout.addLayout(left_layout, stretch=0)
        main_layout.addWidget(utils.create_separator())
        main_layout.addLayout(right_layout, stretch=1)
        central_widget.setLayout(main_layout)
        left_layout.addLayout(TemperatureSection(self.__temps, self.__names, self.__temp_source))
        left_layout.addWidget(utils.create_separator(horizontal=True))
        left_layout.addWidget(list_widget)
        right_layout.addLayout(device_widget)

    def __create_central_widget(self) -> None:
        """Create central widget."""
        central_widget: QWidget = QWidget()
        central_widget.setAutoFillBackground(True)
        central_widget.setProperty("id", "central")
        utils.force_refresh(central_widget)
        self.__configure_layouts(central_widget)
        self.setCentralWidget(central_widget)

    @override
    def closeEvent(self, a0: QCloseEvent|None) -> None:
        """Override the close event to handle application minimize to system tray."""
        if a0:
            a0.ignore()
        if not AppConfig.get("minimize_on_exit", value_type=bool):
            self.__close()
            return
        QTimer.singleShot(0, self.hide)
        self.__tray_icon.showMessage(
            "Minimized to Tray",
            "Your app is still running in the background.",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )

    @override
    def changeEvent(self, event: QEvent) -> None:
        """Override the change event to handle application minimize to system tray."""
        if event and event.type() == QEvent.Type.WindowStateChange\
            and self.windowState() & Qt.WindowState.WindowMinimized:
            QTimer.singleShot(0, self.hide)
            self.__tray_icon.showMessage("Minimized to Tray",
                                         "App is still running in the background.",
                                         QSystemTrayIcon.MessageIcon.Information,
                                         3000)
        super().changeEvent(event)

def main() -> int:
    """Start point."""
    app_name: str = "Finally NZXT Fan control"
    app: Application = Application(app_name=app_name)
    theme_manager: ThemeManager = ThemeManager(app)
    MainWindow(app_name=app_name, theme_manager=theme_manager)
    app.exec()
    return 0

if "__main__" == __name__:
    sys.exit(main())
