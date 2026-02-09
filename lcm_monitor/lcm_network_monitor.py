#!/usr/bin/env python3
"""LCM Network Monitor - Real-time monitoring and visualization of LCM network traffic."""

import sys
import time
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
from lcm_monitor.lcm_spy import LCMMessageSpy
from lcm_monitor.inspector_window import MessageInspectorWindow


class MainWindow(QMainWindow):
    """Main application window showing LCM network traffic overview."""
    
    DEFAULT_UPDATE_RATE_MS = 1000
    DEFAULT_N_SAMPLES = 30
    
    def __init__(self, udpm_url):
        super().__init__()

        # Configuration
        self.udpm_url = udpm_url
        self.update_rate_ms = self.DEFAULT_UPDATE_RATE_MS
        self.n_samples = self.DEFAULT_N_SAMPLES
        self.last_message_time = 0

        # LCM setup
        self.lcm = lcm.LCM(self.udpm_url)
        self.spy = LCMMessageSpy(self.n_samples)
        self.running = True
        self.subscription = self.lcm.subscribe(".*", self.spy.handle_message)
        
        # Window properties
        self.setWindowTitle(f"LCM Network Monitor - {udpm_url}")
        self.setMinimumSize(800, 400)
        self.setGeometry(200, 200, 1000, 600)

        self._setup_ui()
        self.inspector_windows = {}
        
        # Start background LCM handling thread
        self.lcm_thread = threading.Thread(target=self._lcm_handler_loop, daemon=True)
        self.lcm_thread.start()

        # Start GUI update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.start(self.update_rate_ms)
        
        self.show()
        
        # Restore window geometry after show
        settings = QSettings("LCMMonitor", "MainWindow")
        geometry = settings.value("geometry", None)
        if geometry:
            self.restoreGeometry(geometry)

    def _setup_ui(self):
        """Initialize UI components."""
        # Toolbar
        self._setup_toolbar()
        
        # Main table
        self.traffic_table = pg.TableWidget()
        self.traffic_table.verticalHeader().setVisible(False)
        self.traffic_table.setAlternatingRowColors(True)
        self.traffic_table.cellClicked.connect(self._open_inspector_window)
        self.traffic_table.horizontalHeader().sectionDoubleClicked.connect(self._sort_by_column)
        self.traffic_table.setData(self.spy.traffic_data())
        self.current_sort_column = None
        self.sort_ascending = True
        
        # Empty state label
        self.empty_label = QLabel("Waiting for LCM messages...")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #888888; font-size: 16px; padding: 50px;")
        
        # Stack widget to switch between table and empty state
        self.stack = QStackedWidget()
        self.stack.addWidget(self.traffic_table)
        self.stack.addWidget(self.empty_label)
        self.setCentralWidget(self.stack)
        
        # Status bar
        status_bar = self.statusBar()
        status_bar.showMessage('Ready', 5000)
        
        # Connection indicator
        self.connection_indicator = QLabel("●")
        self.connection_indicator.setStyleSheet("color: #888888; font-size: 16px;")
        self.connection_indicator.setToolTip("Connection status")
        status_bar.addPermanentWidget(self.connection_indicator)
        
        # Channel count
        self.channel_count_label = QLabel("0 channels")
        status_bar.addPermanentWidget(self.channel_count_label)
        
        # Traffic label
        self.traffic_label = QLabel("Total: 0.00 KB/s")
        status_bar.addPermanentWidget(self.traffic_label)
     
    def _setup_toolbar(self):
        """Setup application toolbar."""
        toolbar = self.addToolBar('Main')
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        
        # Import Types action
        import_action = QAction("Import Types", self)
        import_action.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        import_action.setShortcut(QKeySequence("Ctrl+I"))
        import_action.setToolTip("Import LCM type definitions (Ctrl+I)")
        import_action.triggered.connect(self._import_types)
        toolbar.addAction(import_action)
        
        toolbar.addSeparator()
        
        # Clear Statistics action
        clear_action = QAction("Clear", self)
        clear_action.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        clear_action.setShortcut(QKeySequence("Ctrl+K"))
        clear_action.setToolTip("Clear all statistics (Ctrl+K)")
        clear_action.triggered.connect(self._clear_statistics)
        toolbar.addAction(clear_action)
        
        toolbar.addSeparator()
        
        # Properties action
        props_action = QAction("Properties", self)
        props_action.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        props_action.setToolTip("Configure monitor settings")
        props_action.triggered.connect(self._show_properties_dialog)
        toolbar.addAction(props_action)
    
    def _sort_data(self, data, column, ascending=True):
        """Sort data by specified column.
        
        Args:
            data: List of dictionaries to sort
            column: Column index to sort by
            ascending: Sort in ascending order if True
            
        Returns:
            Sorted list of dictionaries
        """
        headers = ["Channel", "Type", "Num Msgs", "Hz", "1/Hz", "Jitter", "Bandwidth", "Decodable"]
        if column >= len(headers):
            return data
        
        column_name = headers[column]
        
        # Sort data (make a copy to avoid modifying original)
        sorted_data = list(data)
        
        if column_name in ["Num Msgs"]:
            # Numeric columns
            sorted_data.sort(key=lambda x: x.get(column_name, 0), reverse=not ascending)
        elif column_name in ["Hz", "1/Hz", "Jitter", "Bandwidth"]:
            # Extract numeric part from formatted strings
            def extract_number(x):
                val = x.get(column_name, "0")
                try:
                    return float(str(val).split()[0])
                except:
                    return 0
            sorted_data.sort(key=extract_number, reverse=not ascending)
        else:
            # String columns
            sorted_data.sort(key=lambda x: x.get(column_name, ""), reverse=not ascending)
        
        return sorted_data
    
    def _sort_by_column(self, column):
        """Sort table by double-clicked column header."""
        # Toggle sort order if same column clicked
        if self.current_sort_column == column:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_ascending = True
            self.current_sort_column = column
        
        # Force immediate update with new sort order
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
        """Open message inspector window for selected channel.
        
        Args:
            row: Table row clicked
            col: Table column clicked
        """
        item = self.traffic_table.item(row, 0)
        if not item:
            return
        
        channel = item.text()
        if not channel:
            return
        
        # Create new inspector window (or bring existing one to front)
        window = MessageInspectorWindow(channel, self.spy)
        self.inspector_windows[channel] = window
        
    def _apply_table_formatting(self):
        """Apply color coding to table cells."""
        # Color-code the Decodable column
        decodable_col = 7  # "Decodable" column index
        for row in range(self.traffic_table.rowCount()):
            item = self.traffic_table.item(row, decodable_col)
            if item:
                if item.text() == "True":
                    item.setForeground(QColor("#4CAF50"))  # Green
                elif item.text() == "False":
                    item.setForeground(QColor("#F44336"))  # Red
    
    def _update_display(self):
        """Update main window display with latest statistics."""
        data = self.spy.traffic_data()
        
        # Apply current sort order if set
        if self.current_sort_column is not None:
            data = self._sort_data(data, self.current_sort_column, self.sort_ascending)
        
        # Show empty state or table
        with self.spy.lock:
            has_data = len(self.spy.stats) > 0
        
        if has_data:
            self.stack.setCurrentWidget(self.traffic_table)
            self.traffic_table.setData(data)
            self._apply_table_formatting()
            self.traffic_table.horizontalHeader().setStretchLastSection(True)
        else:
            self.stack.setCurrentWidget(self.empty_label)
        
        # Update status bar
        total_bw, bw_unit = self.spy.total_traffic()
        self.traffic_label.setText(f"Total: {total_bw:.2f} {bw_unit}")
        
        # Update channel count
        with self.spy.lock:
            channel_count = len(self.spy.stats)
        self.channel_count_label.setText(f"{channel_count} channel{'s' if channel_count != 1 else ''}")
        
        # Update connection indicator
        current_time = time.time()
        with self.spy.lock:
            # Check if any messages received in last 2 seconds
            active = any(
                (current_time - stats.timestamps[-1]) < 2.0 if len(stats.timestamps) > 0 else False
                for stats in self.spy.stats.values()
            )
        
        if active:
            self.connection_indicator.setStyleSheet("color: #4CAF50; font-size: 16px;")
            self.connection_indicator.setToolTip("Receiving messages")
        else:
            self.connection_indicator.setStyleSheet("color: #888888; font-size: 16px;")
            self.connection_indicator.setToolTip("Idle")

    def _show_properties_dialog(self):
        """Show properties configuration dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Monitor Properties")
        dialog.setGeometry(100, 100, 300, 200)
        
        layout = QVBoxLayout()
        
        # UDPM URL (read-only for now)
        layout.addWidget(QLabel("UDPM URL:"))
        udpm_edit = QLineEdit(self.udpm_url)
        udpm_edit.setReadOnly(True)
        layout.addWidget(udpm_edit)
        
        # Refresh rate
        layout.addWidget(QLabel("Refresh Rate (ms):"))
        refresh_edit = QLineEdit(str(self.update_rate_ms))
        layout.addWidget(refresh_edit)
        
        # Number of samples for statistics
        layout.addWidget(QLabel("Statistics Window (samples):"))
        samples_edit = QLineEdit(str(self.n_samples))
        layout.addWidget(samples_edit)
        
        def save_settings():
            try:
                new_rate = int(refresh_edit.text())
                new_samples = int(samples_edit.text())
                
                self.update_rate_ms = new_rate
                self.n_samples = new_samples
                
                # Restart timer with new rate
                self.update_timer.stop()
                self.update_timer.start(self.update_rate_ms)
                
                dialog.close()
            except ValueError:
                print("Invalid input: please enter integers")
        
        save_button = QPushButton("Save")
        save_button.clicked.connect(save_settings)
        layout.addWidget(save_button)
        
        dialog.setLayout(layout)
        dialog.exec()

    def _lcm_handler_loop(self):
        """Background thread for handling LCM messages."""
        while self.running:
            # Use timeout to allow periodic checking of self.running flag
            self.lcm.handle_timeout(100)


def main(app=None):
    """Application entry point.
    
    Args:
        app: Existing QApplication instance, or None to create a new one
    """
    udpm_url = get_cmd_option(sys.argv, "-u=", "udpm://239.255.76.67:7667?ttl=1")
    
    if app is None:
        app = QApplication(sys.argv)
        app.setStyleSheet(APP_STYLESHEET)
        app.setOrganizationName("LCMMonitor")
        app.setApplicationName("LCM Network Monitor")
    
    window = MainWindow(udpm_url)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
