"""NZXT Device manager."""

import atexit
from dataclasses import dataclass
from typing import override

from liquidctl.driver import find_liquidctl_devices
from liquidctl.driver.smart_device import SmartDevice2
from PySide6.QtCore import QThread, Slot
from src.utils.signals import GLOBAL_SIGNALS
from src.widgets.settings_dialog import ServerConfiguration


@dataclass
class DeviceChannel:
    """Device channel information class."""

    speed: int
    rpm: int

@dataclass
class DeviceInformation:
    """Device information class."""

    device: SmartDevice2
    channels: dict[str, DeviceChannel]

class Worker(QThread):
    """Get device RPM information."""

    def __init__(self, devices: list[SmartDevice2],
                       server_configuration: ServerConfiguration) -> None:
        """Initialize device RPM information gatherer."""
        super().__init__()
        self.__server_configuration: ServerConfiguration = server_configuration
        self.__devices: dict[int, DeviceInformation] = {}
        self.__number_of_devices: int = 0
        self.__convert_devices_to_dictionary(devices)
        GLOBAL_SIGNALS.update_speed.connect(self.__update_fan_speed_information)

    def __convert_devices_to_dictionary(self, devices: list[SmartDevice2]) -> None:
        """Convert list of devices to usable dictionary."""
        for device_id, device in enumerate(devices):
            channels: list[str] = list(device._speed_channels.keys()) #noqa: SLF001
            information: DeviceInformation = DeviceInformation(device=device, channels={})
            for channel in channels:
                information.channels[channel] = DeviceChannel(speed=0, rpm=0)
                self.__number_of_devices += 1
            self.__devices[device_id] = information

    @Slot(int, str, int)
    def __update_fan_speed_information(self, device_id: int, channel: str, value: int) -> None:
        """Update new fan speed information for later processing."""
        if device_id not in self.__devices:
            return
        device_information: DeviceInformation = self.__devices[device_id]
        if channel not in device_information.channels:
            return
        device_information.channels[channel].speed = value

    def __update_rpm_information(self, device_id: int,
                                       device_information: DeviceInformation) -> None:
        """Update new fan speed information for later processing."""
        reports: list[tuple] = []
        try:
            reports = device_information.device.get_status(max_attempts=6)
        except Exception as _:
            return
        for report in reports:
            if "rpm" in report[-1]:
                channel: str = "".join(report[0].split(" ")[:2]).lower()
                rpm: int = report[1]
                device_information.channels[channel].rpm = rpm
                GLOBAL_SIGNALS.update_rpm.emit(device_id, channel, rpm)

    def __update_fan_speed(self, device_information: DeviceInformation) -> None:
        """Update fan speed of given device and channel."""
        device: SmartDevice2 = device_information.device
        channels: dict[str, DeviceChannel] = device_information.channels
        for channel, information in channels.items():
            try:
                device.set_fixed_speed(channel, information.speed)
                self.msleep(self.__server_configuration.rate // self.__number_of_devices)
            except IndexError:
                ...

    @override
    def run(self) -> None:
        """Override thread body."""
        while True:
            for device_id, device_information in self.__devices.items():
                self.__update_rpm_information(device_id, device_information)
                self.__update_fan_speed(device_information)

class DeviceManager:
    """NZXT Controllers manager."""

    def __init__(self, server_configuration: ServerConfiguration) -> None:
        """Initialize NZXT Controllers."""
        self.__error: bool = False
        self.__devices: list[SmartDevice2] = []
        self.__scan_devices()
        self.__connect_devices()
        atexit.register(self.__disconnect_devices)
        if not self.__devices:
            return
        self.__worker: Worker = Worker(self.__devices, server_configuration)
        self.__worker.start()
        atexit.register(self.__worker.terminate)

    @property
    def error(self) -> bool:
        """Return Error status."""
        return self.__error

    @property
    def devices(self) -> list[SmartDevice2]:
        """Return initialized devices."""
        return self.__devices

    def __scan_devices(self) -> None:
        """Scan available devices."""
        potential_devices: list[SmartDevice2] = list(find_liquidctl_devices())
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
