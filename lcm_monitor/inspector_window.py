"""
Message Inspector Window - Detailed view of LCM message contents.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QLineEdit, 
    QHeaderView, QMenu, QApplication
)
from PyQt5.QtCore import QTimer, Qt, QSettings

from .utils import fill_qtreeitem_with_lcm


class MessageInspectorWindow(QWidget):
    """Window for inspecting detailed LCM message contents."""
    
    def __init__(self, channel, spy):
        super().__init__()
        self.channel = channel
        self.spy = spy
        self.setWindowTitle(f"Inspector - {self.channel}")
        self.setMinimumSize(500, 400)
        
        # Keep track of plot windows to prevent garbage collection
        self.plot_windows = []
        
        # Search bar
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search fields...")
        self.search_box.textChanged.connect(self._filter_tree)
        
        # Tree widget with type column
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Field", "Value", "Type"])
        self.tree.setAlternatingRowColors(True)
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.itemDoubleClicked.connect(self._plot_window)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        
        layout = QVBoxLayout()
        layout.addWidget(self.search_box)
        layout.addWidget(self.tree)
        self.setLayout(layout)
        
        # Update tree widget every second
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(1000)

        self.show()
        
        # Restore window geometry after show
        settings = QSettings("LCMMonitor", "InspectorWindow")
        geometry = settings.value(f"geometry_{channel}", None)
        if geometry:
            self.restoreGeometry(geometry)
    
    def keyPressEvent(self, event):
        """Handle Escape key to close window."""
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
    
    def closeEvent(self, event):
        """Save window geometry on close."""
        settings = QSettings("LCMMonitor", "InspectorWindow")
        settings.setValue(f"geometry_{self.channel}", self.saveGeometry())
        event.accept()
    
    def _show_context_menu(self, position):
        """Show context menu with copy option."""
        item = self.tree.itemAt(position)
        if not item:
            return
        
        menu = QMenu(self)
        copy_action = menu.addAction("Copy Value")
        copy_field_action = menu.addAction("Copy Field Name")
        
        action = menu.exec_(self.tree.viewport().mapToGlobal(position))
        
        if action == copy_action:
            value = item.text(1)
            QApplication.clipboard().setText(value)
        elif action == copy_field_action:
            field = item.text(0)
            QApplication.clipboard().setText(field)
    
    def _filter_tree(self, text):
        """Filter tree items based on search text."""
        def filter_item(item, text):
            match = text.lower() in item.text(0).lower() or text.lower() in item.text(1).lower()
            item.setHidden(not match and text != "")
            
            # Check children
            child_match = False
            for i in range(item.childCount()):
                if filter_item(item.child(i), text):
                    child_match = True
            
            # Show parent if any child matches
            if child_match:
                item.setHidden(False)
            
            return match or child_match
        
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            filter_item(root.child(i), text)

    def _plot_window(self, item, column):
        """Open plot window for selected numeric field on double-click.
        
        Args:
            item: QTreeWidgetItem that was double-clicked
            column: Column index that was double-clicked
        """
        # Import here to avoid circular dependency
        from .plot_window import PlotWindow
        
        if not item:
            return
        
        # Build full field path from tree hierarchy
        path_parts = []
        current = item
        while current is not None:
            field_name = current.text(0)
            if field_name and field_name != self.channel:
                path_parts.insert(0, field_name)
            parent = current.parent()
            # Stop at invisible root (parent returns the root item for top-level items)
            if parent is None or parent.text(0) == '':
                break
            current = parent
        
        if not path_parts:
            return
        
        # Get the message
        with self.spy.lock:
            msg = self.spy.msg.get(self.channel)
        
        if msg is None:
            return
        
        # Navigate to the field/value
        try:
            value = msg
            full_path = []
            for part in path_parts:
                full_path.append(part)
                if part.startswith('[') and part.endswith(']'):
                    # Array index
                    index = int(part[1:-1])
                    value = value[index]
                else:
                    # Attribute
                    value = getattr(value, part)
            
            # Check if value is numeric (plottable)
            if isinstance(value, (int, float)):
                field_path = '.'.join(full_path)
                plot_window = PlotWindow(self.spy, self.channel, field_path)
                self.plot_windows.append(plot_window)
            else:
                print(f"Field '{'.'.join(full_path)}' is not numeric (type: {type(value).__name__})")
        except (AttributeError, IndexError, ValueError) as e:
            print(f"Cannot access field: {e}")
   
    def update(self):
        """Update tree with latest message contents."""
        self.tree.clear()
        
        with self.spy.lock:
            msg = self.spy.msg.get(self.channel)
        
        if msg is None:
            return
        
        root_item = self.tree.invisibleRootItem()
        fill_qtreeitem_with_lcm(root_item, msg)
        self.tree.expandAll()
