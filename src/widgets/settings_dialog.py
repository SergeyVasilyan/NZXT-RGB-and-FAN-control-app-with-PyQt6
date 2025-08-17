"""Settings dialog."""

from dataclasses import dataclass

from PyQt6.QtCore import QRegularExpression, Qt
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


@dataclass
class ServerConfiguration:
    """Server Configuration."""

    ip: str = "0.0.0.0"
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

if "__main__" == __name__:
    ...
