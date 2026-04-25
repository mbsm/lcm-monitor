#!/usr/bin/env python3
"""LCM Network Monitor - Real-time monitoring and visualization of LCM network traffic."""

import os
import sys
import threading

os.environ.setdefault("PYQTGRAPH_QT_LIB", "PyQt5")

import lcm
import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QLabel, QLineEdit,
    QAction, QFileDialog, QDialog, QApplication, QStackedWidget,
    QSpinBox, QFormLayout, QDialogButtonBox, QMenu,
    QSplitter, QListWidget, QListWidgetItem,
)
from PyQt5.QtCore import QTimer, Qt, QSettings
from PyQt5.QtGui import QColor, QKeySequence

from lcm_monitor.theme import DARK, app_stylesheet, qpalette
from lcm_monitor.utils import format_bandwidth, get_cmd_option
from lcm_monitor.lcm_spy import COLUMNS, LCMMessageSpy, DECODABLE_COL, sort_traffic_data
from lcm_monitor.host_spy import HostSpy
from lcm_monitor.inspector_window import MessageInspectorWindow


STATUS_ACTIVE = "#2ecc71"
STATUS_IDLE = "#8b919d"
DECODABLE_OK = "#2ecc71"
DECODABLE_FAIL = "#e74c3c"

# Identifier-style columns are centered; everything else (counts, rates,
# bandwidth) is right-aligned so digits line up vertically.
_CENTERED_COLUMNS = frozenset(
    COLUMNS.index(n) for n in ("Channel", "Type", "Decodable")
)


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
        self.host_spy = HostSpy(self.udpm_url, self.DEFAULT_N_SAMPLES)
        self.running = True
        self.subscription = self.lcm.subscribe(".*", self.spy.handle_message)
        self._last_spy_gen = -1
        self._last_host_gen = -1
        self._last_hosts_gen = -1
        self._connection_active = None
        self._selected_host_ip = None  # None = "All hosts"
        self._host_items = {}  # ip -> QListWidgetItem

        self.setWindowTitle(f"LCM Network Monitor - {udpm_url}")
        self.setMinimumSize(800, 400)
        self.setGeometry(200, 200, 1000, 600)

        self._setup_ui()
        self.inspector_windows = {}

        self.lcm_thread = threading.Thread(target=self._lcm_handler_loop, daemon=True)
        self.lcm_thread.start()
        self.host_spy.start()

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.start(self.update_rate_ms)

        settings = QSettings("LCMMonitor", "MainWindow")
        geometry = settings.value("geometry", None)
        if geometry:
            self.restoreGeometry(geometry)
        self.show()

    def _setup_ui(self):
        """Initialize UI components."""
        self._setup_actions()
        self._setup_menu_bar()

        self.traffic_table = pg.TableWidget()
        self.traffic_table.verticalHeader().setVisible(False)
        self.traffic_table.setAlternatingRowColors(True)
        self.traffic_table.setShowGrid(False)
        self.traffic_table.horizontalHeader().setStretchLastSection(True)
        self.traffic_table.cellDoubleClicked.connect(self._open_inspector_window)
        self.traffic_table.horizontalHeader().sectionDoubleClicked.connect(self._sort_by_column)
        self.traffic_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.traffic_table.customContextMenuRequested.connect(self._show_table_context_menu)
        self.current_sort_column = None
        self.sort_ascending = True

        self.empty_label = QLabel("Waiting for LCM messages...")
        self.empty_label.setObjectName("EmptyState")
        self.empty_label.setAlignment(Qt.AlignCenter)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.traffic_table)
        self.stack.addWidget(self.empty_label)
        self.stack.setCurrentWidget(self.empty_label)

        self.hosts_list = QListWidget()
        self.hosts_list.setObjectName("HostsPanel")
        self.hosts_list.setMinimumWidth(180)
        self.hosts_list.itemSelectionChanged.connect(self._on_host_selection_changed)

        self._all_hosts_item = QListWidgetItem("All hosts")
        self._all_hosts_item.setData(Qt.UserRole, None)
        self.hosts_list.addItem(self._all_hosts_item)
        self.hosts_list.setCurrentItem(self._all_hosts_item)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.hosts_list)
        splitter.addWidget(self.stack)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([220, 800])
        self.setCentralWidget(splitter)

        status_bar = self.statusBar()
        status_bar.showMessage('Ready', 5000)

        self.connection_indicator = QLabel("\u25cf")
        self.connection_indicator.setStyleSheet(
            f"color: {STATUS_IDLE}; font-size: 14px; background: transparent;"
        )
        self.connection_indicator.setToolTip("Connection status")
        status_bar.addPermanentWidget(self.connection_indicator)

        self.channel_count_label = QLabel("0 channels")
        status_bar.addPermanentWidget(self.channel_count_label)

        self.traffic_label = QLabel("Total: 0.00 KB/s")
        status_bar.addPermanentWidget(self.traffic_label)

    def _setup_actions(self):
        """Build QActions shared by the menu bar and toolbar."""
        self.import_action = QAction("&Import Types...", self)
        self.import_action.setShortcut(QKeySequence("Ctrl+I"))
        self.import_action.setToolTip("Import LCM type definitions (Ctrl+I)")
        self.import_action.triggered.connect(self._import_types)

        self.clear_action = QAction("&Clear Statistics", self)
        self.clear_action.setShortcut(QKeySequence("Ctrl+K"))
        self.clear_action.setToolTip("Clear all channel statistics (Ctrl+K)")
        self.clear_action.triggered.connect(self._clear_statistics)

        self.properties_action = QAction("&Properties...", self)
        self.properties_action.setShortcut(QKeySequence("Ctrl+,"))
        self.properties_action.setToolTip("Configure monitor settings (Ctrl+,)")
        self.properties_action.triggered.connect(self._show_properties_dialog)

        self.quit_action = QAction("&Quit", self)
        self.quit_action.setShortcut(QKeySequence.Quit)
        self.quit_action.triggered.connect(self.close)

        self.about_action = QAction("&About", self)
        self.about_action.triggered.connect(self._show_about_dialog)

    def _setup_menu_bar(self):
        """Build the application menu bar."""
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(self.import_action)
        file_menu.addAction(self.clear_action)
        file_menu.addSeparator()
        file_menu.addAction(self.quit_action)

        edit_menu = menu_bar.addMenu("&Edit")
        edit_menu.addAction(self.properties_action)

        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction(self.about_action)

    def _show_table_context_menu(self, position):
        """Right-click menu on the traffic table."""
        menu = QMenu(self.traffic_table)
        item = self.traffic_table.itemAt(position)
        if item is not None:
            row = item.row()
            channel_item = self.traffic_table.item(row, 0)
            channel = channel_item.text() if channel_item else None
            if channel:
                inspect_action = menu.addAction(f"Inspect '{channel}'")
                inspect_action.triggered.connect(
                    lambda _checked=False, r=row: self._open_inspector_window(r, 0)
                )
                menu.addSeparator()
        menu.addAction(self.clear_action)
        menu.exec_(self.traffic_table.viewport().mapToGlobal(position))

    def _show_about_dialog(self):
        """Show the About dialog."""
        from . import __version__
        text = (
            f"<b>LCM Network Monitor</b> v{__version__}<br><br>"
            "Real-time monitoring and visualization of LCM network traffic.<br><br>"
            f"Listening on:<br><code>{self.udpm_url}</code>"
        )
        dialog = QDialog(self)
        dialog.setWindowTitle("About LCM Network Monitor")
        label = QLabel(text)
        label.setTextFormat(Qt.RichText)
        label.setWordWrap(True)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(dialog.accept)
        layout = QVBoxLayout(dialog)
        layout.addWidget(label)
        layout.addWidget(buttons)
        dialog.exec_()

    def _sort_by_column(self, column):
        """Sort table by double-clicked column header."""
        if self.current_sort_column == column:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_ascending = True
            self.current_sort_column = column
        self._last_spy_gen = -1
        self._last_host_gen = -1
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
        self.host_spy.stop()
        event.accept()

    def _clear_statistics(self):
        """Clear all accumulated channel statistics."""
        self.spy.clear()
        self.host_spy.clear()
        for ip, item in self._host_items.items():
            row = self.hosts_list.row(item)
            if row >= 0:
                self.hosts_list.takeItem(row)
        self._host_items.clear()
        self._last_hosts_gen = -1

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
        """Set per-column alignment and color-code the Decodable column."""
        col_count = self.traffic_table.columnCount()
        row_count = self.traffic_table.rowCount()

        for col in range(col_count):
            align = (
                Qt.AlignCenter if col in _CENTERED_COLUMNS
                else Qt.AlignRight | Qt.AlignVCenter
            )
            header_item = self.traffic_table.horizontalHeaderItem(col)
            if header_item is not None:
                header_item.setTextAlignment(align)

        for row in range(row_count):
            for col in range(col_count):
                item = self.traffic_table.item(row, col)
                if item is None:
                    continue
                item.setTextAlignment(
                    Qt.AlignCenter if col in _CENTERED_COLUMNS
                    else Qt.AlignRight | Qt.AlignVCenter
                )
                if col == DECODABLE_COL:
                    if item.text() == "True":
                        item.setForeground(QColor(DECODABLE_OK))
                    elif item.text() == "False":
                        item.setForeground(QColor(DECODABLE_FAIL))

    def _update_display(self):
        """Update main window display with latest statistics."""
        data = self.spy.get_display_data()

        # Always update status bar (cheap) — always shows the global view.
        self.traffic_label.setText(f"Total: {data.total_bw:.2f} {data.bw_unit}")
        self.channel_count_label.setText(
            f"{data.channel_count} channel{'s' if data.channel_count != 1 else ''}"
        )

        if data.active != self._connection_active:
            self._connection_active = data.active
            if data.active:
                self.connection_indicator.setStyleSheet(
                    f"color: {STATUS_ACTIVE}; font-size: 14px; background: transparent;"
                )
                self.connection_indicator.setToolTip("Receiving messages")
            else:
                self.connection_indicator.setStyleSheet(
                    f"color: {STATUS_IDLE}; font-size: 14px; background: transparent;"
                )
                self.connection_indicator.setToolTip("Idle")

        self._update_hosts_panel()

        if self._selected_host_ip is None:
            # Unfiltered: drive table from LCMMessageSpy.
            if data.generation == self._last_spy_gen:
                return
            self._last_spy_gen = data.generation
            rows, has_data = data.rows, data.has_data
        else:
            # Filtered: drive table from HostSpy joined with LCMMessageSpy meta.
            if self.host_spy.generation == self._last_host_gen:
                return
            self._last_host_gen = self.host_spy.generation
            rows = self.host_spy.get_channel_rows(
                self._selected_host_ip, self.spy.get_channel_meta()
            )
            has_data = bool(rows)

        if self.current_sort_column is not None:
            rows = sort_traffic_data(rows, self.current_sort_column, self.sort_ascending)

        if has_data:
            self.stack.setCurrentWidget(self.traffic_table)
            self.traffic_table.setData(rows)
            self._apply_table_formatting()
        else:
            self.stack.setCurrentWidget(self.empty_label)

    def _update_hosts_panel(self):
        """Refresh the hosts list with the latest per-host summary."""
        host_rows, gen = self.host_spy.get_host_summary()
        if gen == self._last_hosts_gen:
            return
        self._last_hosts_gen = gen

        seen = set()
        for row in host_rows:
            ip = row["ip"]
            seen.add(ip)
            bw_value, bw_unit = format_bandwidth(row["total_kbps"])
            label = f"●  {ip}    {bw_value:.1f} {bw_unit}"
            color = QColor(STATUS_ACTIVE if row["active"] else STATUS_IDLE)

            item = self._host_items.get(ip)
            if item is None:
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, ip)
                item.setToolTip(
                    f"{ip}\n{row['channel_count']} channel(s)\n{row['msg_count']} packets"
                )
                self.hosts_list.addItem(item)
                self._host_items[ip] = item
            else:
                item.setText(label)
                item.setToolTip(
                    f"{ip}\n{row['channel_count']} channel(s)\n{row['msg_count']} packets"
                )
            item.setForeground(color)

        # If the previously selected host disappeared (e.g. after Clear), fall back to "All hosts".
        if self._selected_host_ip is not None and self._selected_host_ip not in seen:
            self.hosts_list.setCurrentItem(self._all_hosts_item)

    def _on_host_selection_changed(self):
        items = self.hosts_list.selectedItems()
        new_ip = items[0].data(Qt.UserRole) if items else None
        if new_ip == self._selected_host_ip:
            return
        self._selected_host_ip = new_ip
        # Force a redraw on the next tick regardless of which source is active.
        self._last_spy_gen = -1
        self._last_host_gen = -1
        self._update_display()

    def _show_properties_dialog(self):
        """Show properties configuration dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Monitor Properties")
        dialog.setMinimumWidth(360)

        udpm_edit = QLineEdit(self.udpm_url)
        udpm_edit.setReadOnly(True)

        rate_spin = QSpinBox()
        rate_spin.setRange(50, 60_000)
        rate_spin.setSuffix(" ms")
        rate_spin.setValue(self.update_rate_ms)

        samples_spin = QSpinBox()
        samples_spin.setRange(2, 10_000)
        samples_spin.setValue(self.spy.n_samples)

        form = QFormLayout()
        form.addRow("UDPM URL:", udpm_edit)
        form.addRow("Refresh rate:", rate_spin)
        form.addRow("Statistics window:", samples_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        layout = QVBoxLayout(dialog)
        layout.addLayout(form)
        layout.addWidget(buttons)

        if dialog.exec_() != QDialog.Accepted:
            return

        new_rate = rate_spin.value()
        new_samples = samples_spin.value()
        if new_rate != self.update_rate_ms:
            self.update_rate_ms = new_rate
            self.update_timer.start(self.update_rate_ms)
        if new_samples != self.spy.n_samples:
            self.spy.set_sample_window(new_samples)
            self.host_spy.set_sample_window(new_samples)

    def _lcm_handler_loop(self):
        """Background thread for handling LCM messages."""
        while self.running:
            self.lcm.handle_timeout(100)


def _ensure_desktop_entry():
    """On Linux, create .desktop file and install icon on first run."""
    if not sys.platform.startswith('linux'):
        return

    from pathlib import Path
    import shutil

    apps_dir = Path.home() / '.local' / 'share' / 'applications'
    desktop_file = apps_dir / 'lcm-network-monitor.desktop'

    if desktop_file.exists():
        return

    icons_dir = Path.home() / '.local' / 'share' / 'icons'
    icon_src = Path(__file__).parent / 'lcm.png'
    icon_dest = icons_dir / 'lcm-network-monitor.png'

    try:
        icons_dir.mkdir(parents=True, exist_ok=True)
        if icon_src.exists() and not icon_dest.exists():
            shutil.copy2(icon_src, icon_dest)

        apps_dir.mkdir(parents=True, exist_ok=True)
        desktop_file.write_text(f"""\
[Desktop Entry]
Version=1.0
Type=Application
Name=LCM Network Monitor
Comment=Monitor and visualize LCM network traffic
Exec=python3 -m lcm_monitor
Icon={icon_dest}
Terminal=false
Categories=Development;Network;Utility;
Keywords=LCM;Network;Monitor;Traffic;
""")
        desktop_file.chmod(0o755)
    except OSError:
        pass


def main(app=None):
    """Application entry point."""
    _ensure_desktop_entry()

    udpm_url = get_cmd_option(sys.argv, "-u=", "udpm://239.255.76.67:7667?ttl=1")
    types_path = get_cmd_option(sys.argv, "-p=", None)

    if app is None:
        app = QApplication(sys.argv)
        app.setOrganizationName("LCMMonitor")
        app.setApplicationName("LCM Network Monitor")
        app.setPalette(qpalette(DARK))
        app.setStyleSheet(app_stylesheet(DARK))

    window = MainWindow(udpm_url, types_path=types_path)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
