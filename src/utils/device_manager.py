"""NZXT Device manager."""

import atexit
from typing import override
from PySide6.QtCore import QThread
from liquidctl.driver import find_liquidctl_devices, smart_device

from src.utils.signals import GLOBAL_SIGNALS


class Worker(QThread):
    """Get device RPM information."""

    def __init__(self, devices: list[smart_device.SmartDevice2]) -> None:
        """Initialize device RPM information gatherer."""
        super().__init__()
        self.__devices: list[smart_device.SmartDevice2] = devices

    def __get_rpms(self) -> None:
        """Get Fan RPM report form liquidctl."""
        for device_id, device in enumerate(self.__devices):
            reports: list[tuple] = []
            try:
                reports = device.get_status(max_attempts=6)
            except Exception as _:
                continue
            for report in reports:
                if "rpm" in report[-1]:
                    name: str = "".join(report[0].split(" ")[:2]).lower()
                    GLOBAL_SIGNALS.update_rpm.emit(str(device_id), name, report[1])

    @override
    def run(self) -> None:
        """Override thread body."""
        while True:
            self.__get_rpms()
            self.sleep(1)

class DeviceManager:
    """NZXT Controllers manager."""

    def __init__(self) -> None:
        """Initialize NZXT Controllers."""
        self.__error: bool = False
        self.__devices: list[smart_device.SmartDevice2] = []
        self.__scan_devices()
        self.__connect_devices()
        if self.__devices:
            self.__worker: Worker = Worker(self.__devices)
            self.__worker.start()
            atexit.register(self.__worker.terminate)
        atexit.register(self.__disconnect_devices)

    @property
    def error(self) -> bool:
        """Return Error status."""
        return self.__error

    @property
    def devices(self) -> list[smart_device.SmartDevice2]:
        """Return initialized devices."""
        return self.__devices

    def __scan_devices(self) -> None:
        """Scan available devices."""
        potential_devices: list[smart_device.SmartDevice2] = list(find_liquidctl_devices())
        for device in potential_devices:
            if "NZXT" not in device.description:
                continue
            self.__devices.append(device)

    def __connect_devices(self) -> None:
        """Connect all devices."""
        try:
            for device in self.__devices:
                device.connect()
                device.initialize()
        except Exception:
            self.__error = True

    def __disconnect_devices(self) -> None:
        """Disconnect devices."""
        for device in self.__devices:
            device.disconnect()

if "__main__" == __name__:
    ...
