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
    QComboBox,
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)
from src.layouts.device import DeviceSection
from src.layouts.temp import TemperatureSection
from src.utils.common import PathManager
from src.utils.device_manager import DeviceManager
from src.utils.observable_dict import ObservableDict
from src.utils.signals import GLOBAL_SIGNALS
from src.widgets.application import Application
from src.widgets.config import AppConfig
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
        self.__modes: ObservableDict = ObservableDict()
        self.__sources: ObservableDict = ObservableDict()
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
        presets: list[str] = []
        for _, _, files in os.walk(PathManager.PRESETS):
            if not files:
                continue
            for file in files:
                if ".json" in file.lower():
                    presets.append(os.path.splitext(file)[0].title())
        presets.append("Custom")
        self.__device_manager: DeviceManager = DeviceManager(self.__server_config)
        self.__create_system_tray(presets)
        self.setMenuBar(MenuBar(self.__server_config, self.__export_current_configuration,
                                self.__load_configuration, self.__theme_manager, self.__tray_icon))
        self.__create_central_widget(presets)
        if AppConfig.get("start_minimized"):
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
            for config in ["start_minimized", "minimize_on_exit", "theme"]:
                configuration[config] = AppConfig.get(config)
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
        for device_id, fans in configuration.get("devices", {}).items():
            configuration[device_id] = {}
            device_modes: dict[str, Any] = {}
            device_sources: dict[str, Any] = {}
            for fan_id, fan_info in fans.items():
                device_modes[fan_id] = fan_info["mode"]
                device_sources[fan_id] = fan_info["source"]
            self.__modes[device_id] = device_modes
            self.__sources[device_id] = device_sources
        if filename != self.__settings:
            GLOBAL_SIGNALS.imported.emit()
            self.__tray_icon.showMessage("Import Configuration", message, icon, 3000)

    def __load_preset(self, preset: str) -> None:
        """Load selected preset."""
        self.__load_configuration(os.path.join(PathManager.PRESETS, f"{preset.lower()}.json"))

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

    def __create_preset_action(self, preset_menu: QMenu, preset: str) -> None:
        """Create preset QAction."""
        action: QAction = QAction(preset, preset_menu)
        action.triggered.connect(lambda _: self.__load_preset(preset))
        preset_menu.addAction(action)

    def __create_system_tray(self, presets: list[str]) -> None:
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
        preset_menu: QMenu = QMenu("Presets", self)
        preset_menu.setIcon(self.__create_icon("file"))
        for preset in presets:
            self.__create_preset_action(preset_menu, preset)
        tray_menu.addMenu(preset_menu)
        tray_menu.addSeparator()
        tray_menu.addAction(restore_action)
        tray_menu.addAction(quit_action)
        self.__tray_icon.show()

    def __create_preset_section(self, presets: list[str]) -> QHBoxLayout:
        """Create preset section."""
        preset_layout: QHBoxLayout = QHBoxLayout()
        preset_box: QComboBox = QComboBox()
        preset_box.addItems(presets)
        modes: dict[str, Any] = self.__modes.get_data()
        current_modes: list[str] = []
        for fans in modes.values():
            for mode in fans.values():
                if mode not in current_modes:
                    current_modes.append(mode)
        current_preset: str = current_modes[0] if 1 == len(current_modes) else "Custom"
        preset_box.setCurrentText(current_preset)
        preset_box.currentTextChanged.connect(lambda preset: self.__load_preset(preset))
        preset_layout.addWidget(utils.create_label("Preset", size="medium"),
                                alignment=Qt.AlignmentFlag.AlignRight)
        preset_layout.addWidget(preset_box, alignment=Qt.AlignmentFlag.AlignLeft)
        return preset_layout

    def __configure_layouts(self, central_widget: QWidget, presets: list[str]) -> None:
        """Create and configure layouts."""
        main_layout: QVBoxLayout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        main_layout.addLayout(self.__create_preset_section(presets))
        main_layout.addLayout(TemperatureSection(self.__temps, self.__names, self.__temp_source))
        main_layout.addWidget(utils.create_separator(horizontal=True))
        main_layout.addLayout(DeviceSection(self.__device_manager.devices, self.__modes,
                                            self.__sources, self.__temps, self.__min_temp))

    def __create_central_widget(self, presets: list[str]) -> None:
        """Create central widget."""
        central_widget: QWidget = QWidget()
        central_widget.setAutoFillBackground(True)
        central_widget.setProperty("id", "central")
        utils.force_refresh(central_widget)
        self.__configure_layouts(central_widget, presets)
        self.setCentralWidget(central_widget)

    @override
    def closeEvent(self, a0: QCloseEvent|None) -> None:
        """Override the close event to handle application minimize to system tray."""
        if a0:
            a0.ignore()
        if not AppConfig.get("minimize_on_exit"):
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
