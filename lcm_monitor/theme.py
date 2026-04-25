"""Theme palette and app-wide stylesheet for LCM Network Monitor.

Two palettes (DARK, LIGHT) drive a single Qt stylesheet so every widget —
menus, inputs, tree/table, scrollbars, toolbar — stays visually consistent.
Semantic status colors (decodable green / not-decodable red, connection dot)
live with the widgets that use them and are not overridden here.
"""

from dataclasses import dataclass

from PyQt5.QtGui import QColor, QPalette


DARK_MODE_DEFAULT = True


@dataclass(frozen=True)
class Palette:
    window: str
    surface: str
    surface_elevated: str
    alt_row: str
    border: str
    border_subtle: str
    text: str
    text_muted: str
    text_disabled: str
    accent: str
    selection: str
    selection_text: str


DARK = Palette(
    window="#15171c",
    surface="#1a1d23",
    surface_elevated="#20232a",
    alt_row="#1c1f25",
    border="#2a2e38",
    border_subtle="#23272f",
    text="#e4e6eb",
    text_muted="#8b919d",
    text_disabled="#5a5f68",
    accent="#5a9cff",
    selection="#1e3a5f",
    selection_text="#ffffff",
)

LIGHT = Palette(
    window="#f6f7f9",
    surface="#ffffff",
    surface_elevated="#ffffff",
    alt_row="#f0f2f5",
    border="#d0d4db",
    border_subtle="#e4e6ea",
    text="#1f2328",
    text_muted="#57606a",
    text_disabled="#8c959f",
    accent="#0969da",
    selection="#cfe5ff",
    selection_text="#0a0a0a",
)


def qpalette(p: Palette) -> QPalette:
    """Build a QPalette matching ``p`` — needed so native dialogs pick up colors."""
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(p.window))
    pal.setColor(QPalette.WindowText, QColor(p.text))
    pal.setColor(QPalette.Base, QColor(p.surface))
    pal.setColor(QPalette.AlternateBase, QColor(p.alt_row))
    pal.setColor(QPalette.ToolTipBase, QColor(p.surface_elevated))
    pal.setColor(QPalette.ToolTipText, QColor(p.text))
    pal.setColor(QPalette.Text, QColor(p.text))
    pal.setColor(QPalette.Button, QColor(p.surface_elevated))
    pal.setColor(QPalette.ButtonText, QColor(p.text))
    pal.setColor(QPalette.BrightText, QColor("#ff5555"))
    pal.setColor(QPalette.Link, QColor(p.accent))
    pal.setColor(QPalette.Highlight, QColor(p.selection))
    pal.setColor(QPalette.HighlightedText, QColor(p.selection_text))
    pal.setColor(QPalette.Disabled, QPalette.Text, QColor(p.text_disabled))
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(p.text_disabled))
    pal.setColor(QPalette.Disabled, QPalette.WindowText, QColor(p.text_disabled))
    return pal


def app_stylesheet(p: Palette) -> str:
    return f"""
    QWidget {{
        background: {p.window};
        color: {p.text};
        font-size: 13px;
    }}
    QMainWindow, QDialog {{ background: {p.window}; }}

    QMenuBar {{
        background: {p.surface};
        color: {p.text};
        border-bottom: 1px solid {p.border_subtle};
        padding: 2px 4px;
    }}
    QMenuBar::item {{
        background: transparent;
        padding: 4px 10px;
        border-radius: 3px;
    }}
    QMenuBar::item:selected {{
        background: {p.selection};
        color: {p.selection_text};
    }}
    QMenu {{
        background: {p.surface_elevated};
        color: {p.text};
        border: 1px solid {p.border};
        padding: 4px;
    }}
    QMenu::item {{
        padding: 5px 20px 5px 16px;
        border-radius: 3px;
    }}
    QMenu::item:selected {{
        background: {p.selection};
        color: {p.selection_text};
    }}
    QMenu::separator {{
        height: 1px;
        background: {p.border_subtle};
        margin: 4px 6px;
    }}

    QToolBar {{
        background: {p.window};
        border: none;
        border-bottom: 1px solid {p.border_subtle};
        spacing: 2px;
        padding: 3px 6px;
    }}
    QToolBar::separator {{
        background: {p.border_subtle};
        width: 1px;
        margin: 5px 8px;
    }}
    QToolButton {{
        background: transparent;
        color: {p.text_muted};
        border: 1px solid transparent;
        border-radius: 4px;
        padding: 4px 10px;
        font-weight: 500;
    }}
    QToolButton:hover {{
        background: {p.surface_elevated};
        color: {p.text};
        border-color: {p.border};
    }}
    QToolButton:pressed, QToolButton:checked {{
        background: {p.selection};
        color: {p.selection_text};
        border-color: {p.accent};
    }}

    QLabel {{ background: transparent; }}

    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
        background: {p.surface_elevated};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: 4px;
        padding: 4px 6px;
        selection-background-color: {p.selection};
        selection-color: {p.selection_text};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
    QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {p.accent};
    }}
    QLineEdit:disabled, QTextEdit:disabled,
    QSpinBox:disabled, QDoubleSpinBox:disabled {{
        color: {p.text_disabled};
    }}

    QPushButton {{
        background: {p.surface_elevated};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: 4px;
        padding: 5px 14px;
        min-width: 72px;
    }}
    QPushButton:hover {{ border-color: {p.accent}; }}
    QPushButton:pressed {{
        background: {p.selection};
        color: {p.selection_text};
    }}
    QPushButton:default {{ border-color: {p.accent}; }}
    QPushButton:disabled {{ color: {p.text_disabled}; }}

    QCheckBox {{ background: transparent; spacing: 6px; }}
    QCheckBox::indicator {{
        width: 14px;
        height: 14px;
        border: 1px solid {p.border};
        border-radius: 3px;
        background: {p.surface_elevated};
    }}
    QCheckBox::indicator:hover {{ border-color: {p.accent}; }}
    QCheckBox::indicator:checked {{
        background: {p.accent};
        border-color: {p.accent};
    }}

    QSplitter::handle {{ background: {p.border_subtle}; }}
    QSplitter::handle:horizontal {{ width: 4px; }}
    QSplitter::handle:vertical   {{ height: 4px; }}
    QSplitter::handle:hover {{ background: {p.accent}; }}

    QTreeWidget, QListWidget, QTableWidget {{
        background: {p.surface};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: 8px;
        alternate-background-color: {p.alt_row};
        gridline-color: {p.border_subtle};
        outline: 0;
        show-decoration-selected: 1;
    }}
    QTreeWidget::item, QTableWidget::item {{
        padding: 3px 4px;
        border: none;
    }}
    QListWidget::item {{
        padding: 3px 2px;
        border: none;
    }}
    QTreeWidget::item:hover,
    QListWidget::item:hover,
    QTableWidget::item:hover {{
        background: {p.alt_row};
    }}
    QTreeWidget::item:selected,
    QListWidget::item:selected,
    QTableWidget::item:selected {{
        background: {p.selection};
        color: {p.selection_text};
    }}

    QHeaderView {{ background: {p.surface}; }}
    QHeaderView::section {{
        background: {p.surface};
        color: {p.text_muted};
        border: none;
        border-bottom: 1px solid {p.border};
        padding: 5px 10px;
        font-weight: 600;
    }}
    QHeaderView::section:hover {{ color: {p.text}; }}
    QTableCornerButton::section {{
        background: {p.surface};
        border: none;
        border-bottom: 1px solid {p.border};
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {p.border};
        min-height: 24px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {p.text_muted}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: {p.border};
        min-width: 24px;
        border-radius: 5px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {p.text_muted}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}

    QStatusBar {{
        background: {p.surface};
        color: {p.text_muted};
        border-top: 1px solid {p.border_subtle};
    }}
    QStatusBar::item {{ border: none; }}

    QToolTip {{
        background: {p.surface_elevated};
        color: {p.text};
        border: 1px solid {p.border};
        padding: 4px 6px;
    }}

    QStackedWidget {{ background: {p.window}; }}

    #EmptyState {{
        color: {p.text_muted};
        font-size: 15px;
        padding: 50px;
        background: transparent;
    }}
    """
