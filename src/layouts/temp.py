"""Temperature Section."""


import src.utils.common as utils
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout
from src.utils.observable_dict import ObservableDict


class TemperatureSection(QHBoxLayout):
    """Temperature Section."""

    def __init__(self, temps: ObservableDict, names: ObservableDict) -> None:
        """INIT."""
        super().__init__()
        sources: list[str] = ["CPU", "GPU"]
        for source in sources:
            self.addLayout(self.__create_temp_layout(source, temps, names))
            if source != sources[-1]:
                self.addWidget(utils.create_separator())

    @staticmethod
    def __update_temp_label(temps: dict[str, float], source: str, label: QLabel) -> None:
        """Update temperature label."""
        new_temp: float = temps.get(source, 0)
        label.setText(f"{new_temp} C")
        label.setStyleSheet(f"color: hsl({100 - new_temp}, 100%, 50%);")   

    def __create_temp_layout(self, source: str, temps: ObservableDict, names: ObservableDict) -> QVBoxLayout:
        """Create Temp layout."""
        temp_layout: QVBoxLayout = QVBoxLayout()
        source_label: QLabel = utils.create_label(source, size="large", target="source")
        name_label: QLabel = utils.create_label("N/A", size="small", target="source")
        temp_label: QLabel = utils.create_label(f"{temps[source]} C", size="medium")
        temps.value_changed.connect(lambda temps: self.__update_temp_label(temps, source,
                                                                           temp_label))
        names.value_changed.connect(lambda names: name_label.setText(names.get(source, "N/A")))
        temp_layout.addWidget(source_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        temp_layout.addWidget(name_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        temp_layout.addWidget(temp_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        temp_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        return temp_layout
