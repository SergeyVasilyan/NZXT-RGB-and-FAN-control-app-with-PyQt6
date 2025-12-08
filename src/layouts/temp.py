"""Temperature Section."""

import src.utils.common as utils
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QVBoxLayout
from src.utils.observable_dict import ObservableDict


class TemperatureSection(QHBoxLayout):
    """Temperature Section."""

    def __init__(self, temps: ObservableDict, names: ObservableDict,
                       temp_source: dict[str, str]) -> None:
        """INIT."""
        super().__init__()
        self.__temp_source: dict[str, str] = temp_source
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

    def __update_temp_source(self, source: str, new_source: str) -> None:
        """Update temperature source."""
        if "Package" == new_source:
            new_source = f"CPU {new_source}"
        elif "CPU" == source:
            new_source = f"Core {new_source}"
        else:
            new_source = f"{source} {new_source}"
        self.__temp_source[source] = new_source

    def __create_header(self, source: str) -> QHBoxLayout:
        """Create header layout."""
        header_layout: QHBoxLayout = QHBoxLayout()
        source_label: QLabel = utils.create_label(source, size="large", target="source")
        source_box: QComboBox = QComboBox()
        sources: list[str] = ["Max", "Average", "Package"]
        if "GPU" == source:
            sources = ["Core", "Hot Spot"]
        source_box.addItems(sources)
        source_box.currentTextChanged.connect(lambda new_source: self.__update_temp_source(source,
                                                                                        new_source))
        source_box.setCurrentText(" ".join(self.__temp_source[source].split(" ")[1:]))
        header_layout.addWidget(source_label, alignment=Qt.AlignmentFlag.AlignLeft)
        header_layout.addWidget(source_box, alignment=Qt.AlignmentFlag.AlignRight)
        return header_layout

    def __create_temp_layout(self, source: str, temps: ObservableDict,
                                   names: ObservableDict) -> QVBoxLayout:
        """Create Temp layout."""
        temp_layout: QVBoxLayout = QVBoxLayout()
        name_label: QLabel = utils.create_label("N/A", size="small", target="source")
        temp_label: QLabel = utils.create_label(f"{temps[source]} C", size="medium")
        temps.value_changed.connect(lambda temps: self.__update_temp_label(temps, source,
                                                                           temp_label))
        names.value_changed.connect(lambda names: name_label.setText(names.get(source, "N/A")))
        temp_layout.addLayout(self.__create_header(source))
        temp_layout.addWidget(name_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        temp_layout.addWidget(temp_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        temp_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        return temp_layout
