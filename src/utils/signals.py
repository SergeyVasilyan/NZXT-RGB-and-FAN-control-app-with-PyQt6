"""Global signals across the app."""


from PySide6.QtCore import QObject, Signal


class GlobalSignals(QObject):
    """Global Singals class."""

    update_rpm: Signal = Signal(str, str, int)
    imported: Signal = Signal()

GLOBAL_SIGNALS: GlobalSignals = GlobalSignals()

if "__main__" == __name__:
    ...
