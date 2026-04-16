"""
Base window class for LCM Monitor child windows.
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import QTimer, Qt, QSettings


class MonitorChildWindow(QWidget):
    """Base class with shared geometry persistence, timer, and keyboard behavior."""

    SETTINGS_GROUP = ""

    def __init__(self, settings_key):
        super().__init__()
        self._settings_key = settings_key
        self.timer = QTimer()

    def _start_timer(self, interval_ms, callback):
        self.timer.timeout.connect(callback)
        self.timer.start(interval_ms)

    def _restore_geometry(self):
        settings = QSettings("LCMMonitor", self.SETTINGS_GROUP)
        geometry = settings.value(f"geometry_{self._settings_key}", None)
        if geometry:
            self.restoreGeometry(geometry)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self.timer.stop()
        settings = QSettings("LCMMonitor", self.SETTINGS_GROUP)
        settings.setValue(f"geometry_{self._settings_key}", self.saveGeometry())
        event.accept()
