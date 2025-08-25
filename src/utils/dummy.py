"""Dummy device implementation."""

from dataclasses import dataclass

@dataclass
class DummyChannel:
    """Dummy channel class."""

    mode: str
    rpm: int
    duty: int

class DummyDevice:
    """Dummy device class."""

    def __init__(self, number_of_channels: int=3, max_rpm: int=2_000) -> None:
        """INIT."""
        self.__description: str = f"NZXT Dummy Controller ({number_of_channels} | {max_rpm:_})"
        self.__max_rpm: int = max_rpm
        self.__channels: dict[str, DummyChannel] = {}
        self.__construct_channels(number_of_channels)

    def __construct_channels(self, number_of_channels: int) -> None:
        """Construct dummy channels."""
        for channel in range(1, number_of_channels + 1):
            self.__channels[f"Fan {channel}"] = DummyChannel("PWM", 0, 0)

    @property
    def description(self) -> str:
        """Send description indicating dummy NZXT Controller."""
        return self.__description

    @property
    def _speed_channels(self) -> dict[str, DummyChannel]:
        """Simulate speed channels."""
        return {f"{name.replace(" ", "").lower()}": info for name, info in self.__channels.items()}

    def get_status(self, max_attempts: int=10) -> list[tuple]:
        """Simulate status."""
        status: list[tuple[str, int|str, str]] = []
        for name, info in self.__channels.items():
            status.append((f"{name} control mode", info.mode, ""))
            status.append((f"{name} duty", info.duty, "%"))
            status.append((f"{name} speed", info.rpm, "rpm"))
        return status

    def set_fixed_speed(self, channel: str="", duty: int=0) -> None:
        """Simulate speed change."""
        name: str = channel.replace("fan", "Fan ")
        if name not in self.__channels:
            return
        self.__channels[name].duty = duty
        self.__channels[name].rpm = (self.__max_rpm * duty) // 100

    @staticmethod
    def connect() -> None: ...

    @staticmethod
    def initialize() -> None: ...

    @staticmethod
    def disconnect() -> None: ...

if "__main__" == __name__:
    ...
