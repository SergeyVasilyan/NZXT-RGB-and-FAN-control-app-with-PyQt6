"""About Popup."""

import src.utils.common as utils
from PyQt6.QtWidgets import QWidget, QDialog, QLabel, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt6.QtGui import QDesktopServices, QIcon
from PyQt6.QtCore import QUrl, Qt
from src.widgets.config import AppConfig


class AboutPopup(QDialog):
    """About Popup class."""

    def __init__(self, parent: QWidget|None=None) -> None:
        super().__init__(parent)
        if parent:
            self.setWindowIcon(parent.windowIcon())
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowMaximizeButtonHint)
        self.setWindowTitle("About")
        self.setModal(True)
        self.setFixedSize(400, 300)
        self.__git: str = "https://github.com/SergeyVasilyan/NZXT-RGB-and-FAN-control-app-with-PyQt6"
        self.__construct_layout()

    def __create_icon(self, name: str) -> QIcon:
        """Create themed QIcon."""
        return utils.create_icon(name, AppConfig.get("theme"))

    def __construct_icon(self, ) -> QLabel:
        """Construct Icon section."""
        icon_label: QLabel = QLabel()
        icon_label.setPixmap(self.__create_icon("icon").pixmap(64, 64))
        return icon_label

    def __construct_name(self) -> QLabel:
        """Construct Name section."""
        name_label: QLabel = utils.create_label(f"<h2>{self.parentWidget().windowTitle()}</h2>")
        name_label.setTextFormat(Qt.TextFormat.RichText)
        name_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        return name_label

    def __construct_header(self) -> QHBoxLayout:
        """Construct Header section."""
        header_layout: QHBoxLayout = QHBoxLayout()
        header_layout.addStretch()
        header_layout.addWidget(self.__construct_icon(), alignment=Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(self.__construct_name(), alignment=Qt.AlignmentFlag.AlignVCenter)
        header_layout.addStretch()
        return header_layout

    @staticmethod
    def __construct_license() -> QLabel:
        """Construct License section."""
        license_url: str = "https://www.gnu.org/licenses/gpl-3.0.en.html"
        license_label: QLabel = utils.create_label((
            "This application is licensed under <b>GNU GPLv3</b>.<br>"
            "You are free to use, modify, and distribute under its terms.<br><br>"
            f"<a href='{license_url}'>View full license</a>"
        ))
        license_label.setOpenExternalLinks(True)
        license_label.setTextFormat(Qt.TextFormat.RichText)
        license_label.setWordWrap(True)
        return license_label

    def __construct_changelog(self) -> QPushButton:
        """Construct Changelog button."""
        changelog_url: str = f"{self.__git}/commits/master/"
        changelog_button: QPushButton = QPushButton("View Changelog")
        changelog_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(changelog_url)))
        return changelog_button

    def __construct_contributors(self) -> QPushButton:
        """Construct Contributors button."""
        contributors_url: str = f"{self.__git}/graphs/contributors"
        contributors_button: QPushButton = QPushButton("Contributors")
        contributors_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(contributors_url)))
        return contributors_button

    def __construct_links(self) -> QHBoxLayout:
        """Construct links section."""
        links_layout: QHBoxLayout = QHBoxLayout()
        links_layout.addStretch()
        links_layout.addWidget(self.__construct_changelog(), alignment=Qt.AlignmentFlag.AlignLeft)
        links_layout.addStretch()
        links_layout.addWidget(self.__construct_contributors(),
                               alignment=Qt.AlignmentFlag.AlignRight)
        links_layout.addStretch()
        return links_layout

    def __construct_layout(self) -> None:
        """Construct ."""
        layout: QVBoxLayout = QVBoxLayout()
        layout.addLayout(self.__construct_header())
        layout.addStretch()
        layout.addWidget(utils.create_separator(horizontal=True))
        layout.addStretch()
        layout.addWidget(self.__construct_license())
        layout.addStretch()
        layout.addWidget(utils.create_separator(horizontal=True))
        layout.addStretch()
        layout.addLayout(self.__construct_links())
        layout.addStretch()
        close_button: QPushButton = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(layout)

if "__main__" == __name__:
    ...