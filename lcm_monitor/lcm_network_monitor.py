#!/usr/bin/env python3
"""LCM Network Monitor - Real-time monitoring and visualization of LCM network traffic."""

import sys
import threading

import lcm
import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QAction, QFileDialog, QDialog, QApplication, qApp, QStackedWidget, QStyle
)
from PyQt5.QtCore import QTimer, Qt, QSettings, QSize
from PyQt5.QtGui import QColor, QKeySequence

from lcm_monitor.styles import APP_STYLESHEET
from lcm_monitor.utils import get_cmd_option
from lcm_monitor.lcm_spy import LCMMessageSpy, DECODABLE_COL, sort_traffic_data
from lcm_monitor.inspector_window import MessageInspectorWindow


class MainWindow(QMainWindow):
    """Main application window showing LCM network traffic overview."""

    DEFAULT_UPDATE_RATE_MS = 1000
    DEFAULT_N_SAMPLES = 30

    def __init__(self, udpm_url, types_path=None):
        super().__init__()

        self.udpm_url = udpm_url
        self.update_rate_ms = self.DEFAULT_UPDATE_RATE_MS

        self.lcm = lcm.LCM(self.udpm_url)
        self.spy = LCMMessageSpy(self.DEFAULT_N_SAMPLES, types_path=types_path)
        self.running = True
        self.subscription = self.lcm.subscribe(".*", self.spy.handle_message)
        self._last_generation = -1
        self._connection_active = None

        self.setWindowTitle(f"LCM Network Monitor - {udpm_url}")
        self.setMinimumSize(800, 400)
        self.setGeometry(200, 200, 1000, 600)

        self._setup_ui()
        self.inspector_windows = {}

        self.lcm_thread = threading.Thread(target=self._lcm_handler_loop, daemon=True)
        self.lcm_thread.start()

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.start(self.update_rate_ms)

        self.show()

        settings = QSettings("LCMMonitor", "MainWindow")
        geometry = settings.value("geometry", None)
        if geometry:
            self.restoreGeometry(geometry)

    def _setup_ui(self):
        """Initialize UI components."""
        self._setup_toolbar()

        self.traffic_table = pg.TableWidget()
        self.traffic_table.verticalHeader().setVisible(False)
        self.traffic_table.setAlternatingRowColors(True)
        self.traffic_table.cellDoubleClicked.connect(self._open_inspector_window)
        self.traffic_table.horizontalHeader().sectionDoubleClicked.connect(self._sort_by_column)
        self.current_sort_column = None
        self.sort_ascending = True

        self.empty_label = QLabel("Waiting for LCM messages...")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #888888; font-size: 16px; padding: 50px;")

        self.stack = QStackedWidget()
        self.stack.addWidget(self.traffic_table)
        self.stack.addWidget(self.empty_label)
        self.stack.setCurrentWidget(self.empty_label)
        self.setCentralWidget(self.stack)

        status_bar = self.statusBar()
        status_bar.showMessage('Ready', 5000)

        self.connection_indicator = QLabel("\u25cf")
        self.connection_indicator.setStyleSheet("color: #888888; font-size: 16px;")
        self.connection_indicator.setToolTip("Connection status")
        status_bar.addPermanentWidget(self.connection_indicator)

        self.channel_count_label = QLabel("0 channels")
        status_bar.addPermanentWidget(self.channel_count_label)

        self.traffic_label = QLabel("Total: 0.00 KB/s")
        status_bar.addPermanentWidget(self.traffic_label)

    def _setup_toolbar(self):
        """Setup application toolbar."""
        toolbar = self.addToolBar('Main')
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))

        import_action = QAction("Import Types", self)
        import_action.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        import_action.setShortcut(QKeySequence("Ctrl+I"))
        import_action.setToolTip("Import LCM type definitions (Ctrl+I)")
        import_action.triggered.connect(self._import_types)
        toolbar.addAction(import_action)

        toolbar.addSeparator()

        clear_action = QAction("Clear", self)
        clear_action.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        clear_action.setShortcut(QKeySequence("Ctrl+K"))
        clear_action.setToolTip("Clear all statistics (Ctrl+K)")
        clear_action.triggered.connect(self._clear_statistics)
        toolbar.addAction(clear_action)

        toolbar.addSeparator()

        props_action = QAction("Properties", self)
        props_action.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        props_action.setToolTip("Configure monitor settings")
        props_action.triggered.connect(self._show_properties_dialog)
        toolbar.addAction(props_action)

    def _sort_by_column(self, column):
        """Sort table by double-clicked column header."""
        if self.current_sort_column == column:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_ascending = True
            self.current_sort_column = column
        self._last_generation = -1
        self._update_display()

    def _import_types(self):
        """Open dialog to select and import LCM type directory."""
        path = QFileDialog.getExistingDirectory(
            parent=self,
            caption='Select LCM Types Directory',
            options=QFileDialog.ShowDirsOnly
        )
        if path:
            self.spy.load_types(path)

    def closeEvent(self, event):
        """Save window geometry and clean shutdown."""
        settings = QSettings("LCMMonitor", "MainWindow")
        settings.setValue("geometry", self.saveGeometry())
        self.running = False
        event.accept()
        qApp.quit()

    def _clear_statistics(self):
        """Clear all accumulated channel statistics."""
        self.spy.clear()

    def _open_inspector_window(self, row, col):
        """Open message inspector window for selected channel."""
        item = self.traffic_table.item(row, 0)
        if not item:
            return

        channel = item.text()
        if not channel:
            return

        existing = self.inspector_windows.get(channel)
        if existing is not None and existing.isVisible():
            existing.raise_()
            existing.activateWindow()
            return

        window = MessageInspectorWindow(channel, self.spy)
        self.inspector_windows[channel] = window

    def _apply_table_formatting(self):
        """Apply color coding to the Decodable column."""
        for row in range(self.traffic_table.rowCount()):
            item = self.traffic_table.item(row, DECODABLE_COL)
            if item:
                if item.text() == "True":
                    item.setForeground(QColor("#4CAF50"))
                elif item.text() == "False":
                    item.setForeground(QColor("#F44336"))

    def _update_display(self):
        """Update main window display with latest statistics."""
        data = self.spy.get_display_data()

        # Always update status bar (cheap)
        self.traffic_label.setText(f"Total: {data.total_bw:.2f} {data.bw_unit}")
        self.channel_count_label.setText(
            f"{data.channel_count} channel{'s' if data.channel_count != 1 else ''}"
        )

        if data.active != self._connection_active:
            self._connection_active = data.active
            if data.active:
                self.connection_indicator.setStyleSheet("color: #4CAF50; font-size: 16px;")
                self.connection_indicator.setToolTip("Receiving messages")
            else:
                self.connection_indicator.setStyleSheet("color: #888888; font-size: 16px;")
                self.connection_indicator.setToolTip("Idle")

        # Skip expensive table rebuild if data hasn't changed
        if data.generation == self._last_generation:
            return
        self._last_generation = data.generation

        rows = data.rows
        if self.current_sort_column is not None:
            rows = sort_traffic_data(rows, self.current_sort_column, self.sort_ascending)

        if data.has_data:
            self.stack.setCurrentWidget(self.traffic_table)
            self.traffic_table.setData(rows)
            self._apply_table_formatting()
            self.traffic_table.horizontalHeader().setStretchLastSection(True)
        else:
            self.stack.setCurrentWidget(self.empty_label)

    def _show_properties_dialog(self):
        """Show properties configuration dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Monitor Properties")
        dialog.setGeometry(100, 100, 300, 200)

        layout = QVBoxLayout()

        layout.addWidget(QLabel("UDPM URL:"))
        udpm_edit = QLineEdit(self.udpm_url)
        udpm_edit.setReadOnly(True)
        layout.addWidget(udpm_edit)

        layout.addWidget(QLabel("Refresh Rate (ms):"))
        refresh_edit = QLineEdit(str(self.update_rate_ms))
        layout.addWidget(refresh_edit)

        layout.addWidget(QLabel("Statistics Window (samples):"))
        samples_edit = QLineEdit(str(self.spy.n_samples))
        layout.addWidget(samples_edit)

        def save_settings():
            try:
                new_rate = int(refresh_edit.text())
                new_samples = max(2, min(10000, int(samples_edit.text())))
            except ValueError:
                return

            self.update_rate_ms = new_rate
            self.update_timer.stop()
            self.update_timer.start(self.update_rate_ms)

            if new_samples != self.spy.n_samples:
                self.spy.set_sample_window(new_samples)

            dialog.close()

        save_button = QPushButton("Save")
        save_button.clicked.connect(save_settings)
        layout.addWidget(save_button)

        dialog.setLayout(layout)
        dialog.exec()

    def _lcm_handler_loop(self):
        """Background thread for handling LCM messages."""
        while self.running:
            self.lcm.handle_timeout(100)


def main(app=None):
    """Application entry point."""
    udpm_url = get_cmd_option(sys.argv, "-u=", "udpm://239.255.76.67:7667?ttl=1")
    types_path = get_cmd_option(sys.argv, "-p=", None)

    if app is None:
        app = QApplication(sys.argv)
        app.setStyleSheet(APP_STYLESHEET)
        app.setOrganizationName("LCMMonitor")
        app.setApplicationName("LCM Network Monitor")

    window = MainWindow(udpm_url, types_path=types_path)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
