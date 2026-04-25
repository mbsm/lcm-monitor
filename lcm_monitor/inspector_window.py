"""
Message Inspector Window - Detailed view of LCM message contents.
"""

import logging

from PyQt5.QtWidgets import (
    QVBoxLayout, QTreeWidget, QLineEdit,
    QHeaderView, QMenu, QApplication
)
from PyQt5.QtCore import Qt

from .base_window import MonitorChildWindow
from .utils import fill_qtreeitem_with_lcm, resolve_field_path

log = logging.getLogger(__name__)


class MessageInspectorWindow(MonitorChildWindow):
    """Window for inspecting detailed LCM message contents."""

    SETTINGS_GROUP = "InspectorWindow"

    def __init__(self, channel, spy):
        super().__init__(settings_key=channel)
        self.channel = channel
        self.spy = spy
        self._last_msg = None
        self.setWindowTitle(f"Inspector - {self.channel}")
        self.setMinimumSize(500, 400)

        self.plot_windows = []

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search fields...")
        self.search_box.textChanged.connect(self._filter_tree)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Field", "Value", "Type"])
        self.tree.setAlternatingRowColors(True)
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.itemDoubleClicked.connect(self._open_plot)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)

        layout = QVBoxLayout()
        layout.addWidget(self.search_box)
        layout.addWidget(self.tree)
        self.setLayout(layout)

        self._start_timer(1000, self._refresh_data)
        self._restore_geometry()
        self.show()

    def _show_context_menu(self, position):
        item = self.tree.itemAt(position)
        if not item:
            return

        menu = QMenu(self)
        copy_action = menu.addAction("Copy Value")
        copy_field_action = menu.addAction("Copy Field Name")

        action = menu.exec_(self.tree.viewport().mapToGlobal(position))

        if action == copy_action:
            QApplication.clipboard().setText(item.text(1))
        elif action == copy_field_action:
            QApplication.clipboard().setText(item.text(0))

    def _filter_tree(self, text):
        def filter_item(item, search):
            match = search in item.text(0).lower() or search in item.text(1).lower()
            child_match = any(
                filter_item(item.child(i), search)
                for i in range(item.childCount())
            )
            item.setHidden(not (match or child_match) and search != "")
            return match or child_match

        search = text.lower()
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            filter_item(root.child(i), search)

    def _build_field_path(self, item):
        """Walk up the tree to build a dotted field path from a tree item."""
        parts = []
        current = item
        while current is not None:
            field_name = current.text(0)
            if field_name:
                parts.append(field_name)
            parent = current.parent()
            if parent is None or parent.text(0) == '':
                break
            current = parent
        parts.reverse()
        return '.'.join(parts) if parts else None

    def _open_plot(self, item, column):
        """Open plot window for a numeric field on double-click."""
        from .plot_window import PlotWindow

        if not item:
            return

        field_path = self._build_field_path(item)
        if not field_path:
            return

        with self.spy.lock:
            msg = self.spy.msg.get(self.channel)

        if msg is None:
            return

        try:
            value = resolve_field_path(msg, field_path)
            if isinstance(value, (int, float)):
                self.plot_windows = [w for w in self.plot_windows if w.isVisible()]
                self.plot_windows.append(PlotWindow(self.spy, self.channel, field_path))
        except (AttributeError, IndexError, ValueError):
            log.debug("Cannot resolve field path: %s", field_path)

    def _refresh_data(self):
        with self.spy.lock:
            msg = self.spy.msg.get(self.channel)

        if msg is None or msg is self._last_msg:
            return
        self._last_msg = msg

        self.tree.setUpdatesEnabled(False)
        self.tree.clear()
        fill_qtreeitem_with_lcm(self.tree.invisibleRootItem(), msg)
        self.tree.expandAll()
        self.tree.setUpdatesEnabled(True)
