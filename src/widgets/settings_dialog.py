"""Settings dialog."""

import os
import sys
import win32com.client
from dataclasses import dataclass
from typing import Any, Callable
from win32com.client.dynamic import CDispatch

import src.utils.common as utils
from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QGridLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QWidget,
)
from src.widgets.config import AppConfig
from src.widgets.theme_manager import ThemeManager


@dataclass
class ServerConfiguration:
    """Server Configuration."""

    ip: str = "0.0.0.0"
    port: int = 8085
    rate: float = 1 * 1_000

class SettingsDialog(QDialog):
    """Simple Settings selection Dialog."""

    def __init__(self, config: ServerConfiguration, theme_manager: ThemeManager,
                       export: Callable, parent: QWidget|None=None) -> None:
        """INIT."""
        super().__init__(parent)
        if parent:
            self.setWindowIcon(parent.windowIcon())
        self.setWindowTitle("Settings")
        self.setFixedSize(350, 250)
        self.setModal(True)
        self.__is_windows: bool = "win32" == sys.platform
        self.__task_name: str = "FanControl but Free"
        self.__config: ServerConfiguration = config
        self.__theme_manager: ThemeManager = theme_manager
        self.__export: Callable = export
        self.__port_input: QLineEdit
        self.__rate_spin_box: QDoubleSpinBox
        self.__theme_box: QComboBox
        self.__start_minimized: QCheckBox
        self.__minimize_on_exit: QCheckBox
        self.__start_at_logon: QCheckBox
        self.__create_layout()

    def __add_to_scheduler(self) -> bool:
        """Create task in windows scheduler."""
        domain: str = os.environ.get("USERDOMAIN", "DOMAIN")
        username: str = os.environ.get("USERNAME", "")
        scheduler: CDispatch = win32com.client.Dispatch("Schedule.Service")
        scheduler.Connect()
        root_folder: Any = scheduler.GetFolder("\\")
        task: Any = scheduler.NewTask(0)
        task.RegistrationInfo.Description = self.__task_name
        task.RegistrationInfo.Author = f"{domain}/{username}"
        principal: Any = task.Principal
        principal.LogonType = 3
        principal.RunLevel = 0
        trigger: Any = task.Triggers.Create(9)
        trigger.Enabled = True
        trigger.Id = "LogonTriggerId"
        trigger.UserId = username
        action: Any = task.Actions.Create(0)
        action.Path = "pythonw.exe"
        action.Arguments = "fan_control.py"
        action.WorkingDirectory = os.getcwd()
        settings: Any = task.Settings
        settings.Enabled = True
        settings.Hidden = False
        settings.AllowDemandStart = True
        settings.StartWhenAvailable = True
        try:
            root_folder.RegisterTaskDefinition(self.__task_name, task,
                6,  # TASK_CREATE_OR_UPDATE
                None,  # no user (current user)
                None,  # no password
                3      # TASK_LOGON_INTERACTIVE_TOKEN
            )
        except Exception:
            return False
        return True

    def __remove_from_scheduler(self) -> bool:
        """Create task in windows scheduler."""
        try:
            scheduler: CDispatch = win32com.client.Dispatch("Schedule.Service")
            scheduler.Connect()
            root_folder: Any = scheduler.GetFolder("\\")
            root_folder.DeleteTask(self.__task_name, 0)
        except Exception as e:
            return False
        return True

    def __create_label(self, layout: QGridLayout, text: str, row: int) -> None:
        """Create label."""
        layout.addWidget(utils.create_label(text), row, 0, alignment=Qt.AlignmentFlag.AlignRight)

    def __create_ip_section(self, layout: QGridLayout, row: int) -> int:
        """Create IP section."""
        self.__create_label(layout, "IP Address", row)
        self.__ip_input: QLineEdit = QLineEdit()
        self.__ip_input.setReadOnly(True)
        self.__ip_input.setText(self.__config.ip)
        layout.addWidget(self.__ip_input, row, 1, 1, 2)
        return row + 1

    def __create_port_section(self, layout: QGridLayout, row: int) -> int:
        """Create PORT section."""
        self.__create_label(layout, "Port", row)
        self.__port_input = QLineEdit()
        self.__port_input.setText(str(self.__config.port))
        self.__port_input.setPlaceholderText("Enter Port (1–65535)")
        self.__port_input.setPlaceholderText("Enter IP address")
        port_regex: QRegularExpression = QRegularExpression(
            r"^(6553[0-5]|655[0-2]\d|65[0-4]\d{2}|6[0-4]\d{3}|[1-5]\d{4}|\d{1,4})$"
        )
        self.__port_input.setValidator(QRegularExpressionValidator(port_regex))
        layout.addWidget(self.__port_input, row, 1, 1, 2)
        return row + 1

    def __create_rate_section(self, layout: QGridLayout, row: int) -> int:
        """Create Rate section."""
        self.__create_label(layout, "Rate (in Seconds)", row)
        self.__rate_spin_box = QDoubleSpinBox()
        self.__rate_spin_box.setRange(0.1, 10.0)
        self.__rate_spin_box.setSingleStep(0.1)
        self.__rate_spin_box.setValue(self.__config.rate / 1_000)
        layout.addWidget(self.__rate_spin_box, row, 1, 1 ,2)
        return row + 1

    def __create_theme_section(self, layout: QGridLayout, row: int) -> int:
        """Create theme section."""
        self.__create_label(layout, "Theme", row)
        self.__theme_box: QComboBox = QComboBox()
        themes: list[str] = self.__theme_manager.get_themes()
        currentTheme: str = AppConfig.get("theme")
        self.__theme_box.addItems(themes)
        self.__theme_box.setCurrentText(currentTheme)
        layout.addWidget(self.__theme_box, row, 1, 1, 2)
        return row + 1

    def __create_minimize_section(self, layout: QGridLayout, row: int) -> int:
        """Create Minimize section."""
        self.__create_label(layout, "Start Minimized", row)
        self.__start_minimized = QCheckBox()
        self.__start_minimized.setChecked(AppConfig.get("start_minimized", value_type=bool))
        layout.addWidget(self.__start_minimized, row, 1, 1, 2)
        row += 1
        self.__create_label(layout, "Minimize on Exit", row)
        self.__minimize_on_exit = QCheckBox()
        self.__minimize_on_exit.setChecked(AppConfig.get("minimize_on_exit", value_type=bool))
        layout.addWidget(self.__minimize_on_exit, row, 1, 1, 2)
        return row + 1

    def __create_start_at_logon_section(self, layout: QGridLayout, row: int) -> int:
        """Create startup section."""
        self.__create_label(layout, "Start at User Log On", row)
        self.__start_at_logon = QCheckBox()
        self.__start_at_logon.setChecked(AppConfig.get("start_at_logon", value_type=bool))
        layout.addWidget(self.__start_at_logon, row, 1, 1, 2)
        return row + 1

    def __validate_inputs(self) -> None:
        """Validate IP and PORT."""
        port_text: int = int(self.__port_input.text())
        try:
            port: int = port_text
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Invalid Port", "Port must be an integer between 1 and 65535.")
            return
        rate: float = round(self.__rate_spin_box.value(), 2)
        self.__config.port = port_text
        self.__config.rate = rate * 1_000
        AppConfig.set("start_minimized", self.__start_minimized.isChecked())
        AppConfig.set("minimize_on_exit", self.__minimize_on_exit.isChecked())
        start_at_logon: bool = self.__start_at_logon.isChecked()
        AppConfig.set("start_at_logon", start_at_logon)
        if self.__is_windows:
            if start_at_logon:
                self.__add_to_scheduler()
            else:
                self.__remove_from_scheduler()
        previous_theme: str = AppConfig.get("theme")
        new_theme: str = self.__theme_box.currentText()
        AppConfig.set("theme", new_theme)
        self.__export(settings=True)
        msg: str = "Settings saved successfully."
        if previous_theme != new_theme:
            msg += "\n\nRestart to apply new Theme."
        QMessageBox.information(self, "Success", msg)
        self.close()

    def __create_layout(self) -> None:
        """Create Dialog layout."""
        layout: QGridLayout = QGridLayout()
        row: int = 0
        row = self.__create_ip_section(layout, row)
        row = self.__create_port_section(layout, row)
        row = self.__create_rate_section(layout, row)
        layout.addWidget(utils.create_separator(horizontal=True), row, 0, 1, 3)
        row += 1
        row = self.__create_theme_section(layout, row)
        layout.addWidget(utils.create_separator(horizontal=True), row, 0, 1, 3)
        row += 1
        row = self.__create_minimize_section(layout, row)
        row += 1
        row = self.__create_start_at_logon_section(layout, row)
        submit_btn: QPushButton = QPushButton("Apply")
        submit_btn.clicked.connect(self.__validate_inputs)
        layout.addWidget(submit_btn, row, 0, 1, 3, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(layout)

if "__main__" == __name__:
    ...
