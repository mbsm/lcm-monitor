"""
Stylesheet definitions for LCM Network Monitor.
"""

APP_STYLESHEET = """
QMainWindow, QWidget, QDialog {
    background-color: #2b2b2b;
    color: #e0e0e0;
}

QTableWidget, QTreeWidget {
    background-color: #1e1e1e;
    alternate-background-color: #252525;
    gridline-color: #3a3a3a;
    color: #e0e0e0;
    border: 1px solid #3a3a3a;
}

QTableWidget::item:selected, QTreeWidget::item:selected {
    background-color: #094771;
}

QHeaderView::section {
    background-color: #3a3a3a;
    color: #e0e0e0;
    padding: 5px;
    border: 1px solid #2b2b2b;
    font-weight: bold;
}

QScrollBar:vertical, QScrollBar:horizontal {
    background-color: #2b2b2b;
    width: 12px;
    margin: 0;
}

QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background-color: #555555;
    min-height: 20px;
    border-radius: 6px;
}

QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
    background-color: #666666;
}

QPushButton {
    background-color: #3a3a3a;
    color: #e0e0e0;
    border: 1px solid #555555;
    padding: 5px 15px;
    border-radius: 3px;
}

QPushButton:hover {
    background-color: #4a4a4a;
}

QPushButton:pressed {
    background-color: #094771;
}

QLineEdit {
    background-color: #1e1e1e;
    color: #e0e0e0;
    border: 1px solid #3a3a3a;
    padding: 3px;
    border-radius: 2px;
}

QLabel {
    color: #e0e0e0;
}

QMenuBar {
    background-color: #2b2b2b;
    color: #e0e0e0;
}

QMenuBar::item:selected {
    background-color: #3a3a3a;
}

QMenu {
    background-color: #2b2b2b;
    color: #e0e0e0;
    border: 1px solid #3a3a3a;
}

QMenu::item:selected {
    background-color: #094771;
}

QStatusBar {
    background-color: #2b2b2b;
    color: #e0e0e0;
}

QToolBar {
    background-color: #2b2b2b;
    border: none;
    spacing: 3px;
}

QToolButton {
    background-color: transparent;
    color: #e0e0e0;
    border: none;
    padding: 5px;
}

QToolButton:hover {
    background-color: #3a3a3a;
    border-radius: 3px;
}

QToolButton:pressed {
    background-color: #094771;
}

QSpinBox {
    background-color: #1e1e1e;
    color: #e0e0e0;
    border: 1px solid #3a3a3a;
    padding: 2px;
}

QStackedWidget {
    background-color: #2b2b2b;
}
"""
