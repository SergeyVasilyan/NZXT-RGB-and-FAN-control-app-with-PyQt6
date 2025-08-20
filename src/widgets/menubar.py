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
from src.widgets.theme_manager import ThemeManager


class MenuBar(QMenuBar):
    """Menu Bar"""

    def __init__(self, icons: str, server_config: ServerConfiguration,
                       update_signal: ImportSignal, export_configuration: Callable,
                       load_configuration: Callable, theme_manager: ThemeManager,
                       tray: QSystemTrayIcon) -> None:
        """INIT."""
        super().__init__()
        self.__icons: str = icons
        self.__export: Callable = export_configuration
        self.__load: Callable = load_configuration
        self.__tray: QSystemTrayIcon = tray
        self.__update_signal: ImportSignal = update_signal
        self.__create_file_menu()
        self.__create_settings_menu(server_config, theme_manager)

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
            self.__export(filename=filename)
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

    def __on_network_triggered(self, server_config: ServerConfiguration,
                                     theme_manager: ThemeManager) -> None:
        """On Source Configuration triggered."""
        dialog: SettingsDialog = SettingsDialog(server_config, theme_manager, self.__export, self)
        dialog.exec()

    def __create_file_menu(self) -> None:
        """Create file menu section."""
        file_menu: QMenu = self.addMenu(self.__create_icon("file"), "&File")
        for name, trigger in [("export", self.__on_export_triggered),
                                ("import", self.__on_import_triggered)]:
            action: QAction = QAction(self.__create_icon(name), f"&{name.title()}", file_menu)
            action.triggered.connect(trigger)
            file_menu.addAction(action)

    def __create_settings_menu(self, server_config: ServerConfiguration,
                                     theme_manager: ThemeManager) -> None:
        """Create settings menu."""
        network_action: QAction = self.addAction(self.__create_icon("settings"), "&Settings")
        network_action.triggered.connect(lambda _: self.__on_network_triggered(server_config,
                                                                               theme_manager))
