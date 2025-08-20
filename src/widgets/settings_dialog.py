"""Settings dialog."""

from dataclasses import dataclass
from typing import Callable

import src.utils.common as utils
from PyQt6.QtCore import QRegularExpression, Qt
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtWidgets import (
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
    rate: float = 1.0

class SettingsDialog(QDialog):
    """Simple Settings selection Dialog."""

    def __init__(self, config: ServerConfiguration, theme_manager: ThemeManager,
                       export: Callable, parent: QWidget|None=None) -> None:
        """INIT."""
        super().__init__(parent)
        if parent:
            self.setWindowIcon(parent.windowIcon())
        self.setWindowTitle("Settings")
        self.setFixedSize(300, 250)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowMaximizeButtonHint)
        self.__config: ServerConfiguration = config
        self.__theme_manager: ThemeManager = theme_manager
        self.__export: Callable = export
        self.__ip_input: QLineEdit
        self.__port_input: QLineEdit
        self.__rate_spin_box: QDoubleSpinBox
        self.__start_minimized: QCheckBox
        self.__minimize_on_exit: QCheckBox
        self.__theme_box: QComboBox
        self.__create_layout()

    def __create_label(self, layout: QGridLayout, text: str, row: int) -> None:
        """Create label."""
        layout.addWidget(utils.create_label(text), row, 0, alignment=Qt.AlignmentFlag.AlignRight)

    def __create_ip_section(self, layout: QGridLayout, row: int) -> int:
        """Create IP section."""
        self.__create_label(layout, "IP Address", row)
        self.__ip_input = QLineEdit()
        self.__ip_input.setText(self.__config.ip)
        self.__ip_input.setPlaceholderText("Enter IP address")
        ip_regex: QRegularExpression = QRegularExpression(
            r"^(25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)"
            r"(\.(25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)){3}$"
        )
        self.__ip_input.setValidator(QRegularExpressionValidator(ip_regex))
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
        self.__rate_spin_box.setValue(self.__config.rate)
        layout.addWidget(self.__rate_spin_box, row, 1, 1 ,2)
        return row + 1

    def __create_minimize_section(self, layout: QGridLayout, row: int) -> int:
        """Create Minimize section."""
        self.__create_label(layout, "Start minimized", row)
        self.__start_minimized = QCheckBox()
        self.__start_minimized.setChecked(AppConfig.get("start_minimized"))
        layout.addWidget(self.__start_minimized, row, 1, 1, 2)
        row += 1
        self.__create_label(layout, "Minimize on Exit", row)
        self.__minimize_on_exit = QCheckBox()
        self.__minimize_on_exit.setChecked(AppConfig.get("minimize_on_exit"))
        layout.addWidget(self.__minimize_on_exit, row, 1, 1, 2)
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
            QMessageBox.warning(self, "Invalid Port", "Port must be an integer between 1 and 65535.")
            return
        rate: float = round(self.__rate_spin_box.value(), 2)
        self.__config.ip = ip_text
        self.__config.port = port_text
        self.__config.rate = rate
        AppConfig.set("start_minimized", self.__start_minimized.isChecked())
        AppConfig.set("minimize_on_exit", self.__minimize_on_exit.isChecked())
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
        submit_btn: QPushButton = QPushButton("Apply")
        submit_btn.clicked.connect(self.__validate_inputs)
        layout.addWidget(submit_btn, row, 0, 1, 3, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(layout)

if "__main__" == __name__:
    ...
