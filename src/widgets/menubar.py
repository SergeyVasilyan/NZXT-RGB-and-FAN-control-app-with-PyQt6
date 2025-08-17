"""MenuBar of app."""

import json
from typing import Any, Callable

import src.utils.common as utils
from PyQt6.QtCore import QEvent
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QFileDialog, QMenu, QMenuBar, QSystemTrayIcon
from src.utils.common import ImportSignal
from src.widgets.config import AppConfig
from src.widgets.settings_dialog import ServerConfiguration, SettingsDialog


class MenuBar(QMenuBar):
    """Menu Bar"""

    def __init__(self, icons: str, server_config: ServerConfiguration,
                       update_signal: ImportSignal, export_configuration: Callable,
                       load_configuration: Callable, tray: QSystemTrayIcon) -> None:
        """INIT."""
        super().__init__()
        self.__icons: str = icons
        self.__server_config: ServerConfiguration = server_config
        self.__export: Callable = export_configuration
        self.__load: Callable = load_configuration
        self.__tray: QSystemTrayIcon = tray
        self.__update_signal: ImportSignal = update_signal
        self.__create_file_menu()
        self.__create_settings_menu()

    def __create_icon(self, name: str) -> QIcon:
        """Create themed QIcon."""
        return utils.create_icon(name, self.__icons, AppConfig.get("theme"))

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
                json.dump(self.__export(), f, indent=4)
        except Exception as _:
            message = "Failed to export configuration.\nPlease choose another location."
            icon = QSystemTrayIcon.MessageIcon.Critical
        self.__tray.showMessage("Export Configuration", message, icon, 3000)

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
        self.__load(configuration.get("devices", {}))
        self.__update_signal.update()
        self.__tray.showMessage("Import Configuration", message, icon, 3000)

    def __on_network_triggered(self, _event: QEvent) -> None:
        """On Source Configuration triggered."""
        dialog: SettingsDialog = SettingsDialog(self.__server_config)
        dialog.exec()

    def __create_file_menu(self) -> None:
        """Create file menu section."""
        file_menu: QMenu = self.addMenu(self.__create_icon("file"), "&File")
        for name, trigger in [("export", self.__on_export_triggered),
                                ("import", self.__on_import_triggered)]:
            action: QAction = QAction(self.__create_icon(name), f"&{name.title()}", file_menu)
            action.triggered.connect(trigger)
            file_menu.addAction(action)
    
    def __update_value(self, action: QAction, key: str) -> None:
        """Update start minimized setting."""
        value: bool = not AppConfig.get(key)
        start_icon = self.__create_icon("check" if value else "")
        AppConfig.set(key, value)
        action.setIcon(start_icon)

    def __create_settings_menu(self) -> None:
        """Create settings menu."""
        settings_menu: QMenu = self.addMenu(self.__create_icon("settings"), "&Settings")
        network_action: QAction = QAction(self.__create_icon("network"), "&Source configuration",
                                          settings_menu)
        start_icon: QIcon = self.__create_icon("check" if AppConfig.get("start_minimized") else "")
        start_minimized: QAction = QAction(start_icon, "Start minimized", settings_menu)
        minimize_icon: QIcon = self.__create_icon("check" if AppConfig.get("minimize_on_exit") else "")
        minimize_on_exit: QAction = QAction(minimize_icon, "Minimized on exit", settings_menu)
        network_action.triggered.connect(self.__on_network_triggered)
        start_minimized.triggered.connect(lambda: self.__update_value(start_minimized, "start_minimized"))
        minimize_on_exit.triggered.connect(lambda: self.__update_value(minimize_on_exit, "minimize_on_exit"))
        settings_menu.addAction(network_action)
        settings_menu.addAction(start_minimized)
        settings_menu.addAction(minimize_on_exit)
