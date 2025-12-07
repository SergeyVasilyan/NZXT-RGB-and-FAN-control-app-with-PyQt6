"""Device section of the app."""

from typing import Any

from liquidctl.driver import smart_device
import src.utils.common as utils
from PySide6.QtCore import Slot
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from src.utils.observable_dict import ObservableDict
from src.widgets.curve import FanCurve, FanCurvePoint


class DeviceSection(QHBoxLayout):
    """Device section."""

    def __init__(self, devices: list[smart_device.SmartDevice2], sources: ObservableDict,
                       temps: ObservableDict,
                       curves: dict[str, dict[str, list[FanCurvePoint]]]) -> None:
        """INIT."""
        super().__init__()
        self.__devices: list[smart_device.SmartDevice2] = devices
        self.__sources: ObservableDict = sources
        self.__temps: ObservableDict = temps
        self.__curves: dict[str, dict[str, list[FanCurvePoint]]] = curves
        self.__construct_layout()

    @property
    def curves(self) -> dict[str, dict[str, list[FanCurvePoint]]]:
        """Return current fan curves."""
        return self.__curves

    def __create_device_layout(self, device: Any, device_id: str) -> QWidget:
        """Create Device Layout."""
        widget: QWidget = QWidget()
        widget.setVisible(False)
        layout: QVBoxLayout = QVBoxLayout(widget)
        channels: list[str] = list(device._speed_channels.keys())
        for channel in channels:
            layout.addWidget(FanCurve(self.__temps, self.__sources, device_id, channel,
                                      points=self.__curves.get(device_id, {}).get(channel, None),
                                      parent=self.parentWidget()))
            if channel != channels[-1]:
                layout.addWidget(utils.create_separator(horizontal=True))
        return widget

    def __construct_layout(self) -> None:
        """Construct main layout."""
        for device_id, device in enumerate(self.__devices):
            widget: QWidget = self.__create_device_layout(device, str(device_id))
            self.addWidget(widget)

    @Slot(int)
    def update_layout(self, received_device_id: int) -> None:
        """Construct layout."""
        for device_id in range(self.count()):
            self.itemAt(device_id).widget().setVisible(received_device_id == device_id)
