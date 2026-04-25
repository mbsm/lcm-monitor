"""
Plot Window - Real-time visualization of LCM message fields.
"""

import logging
import os
from collections import deque

os.environ.setdefault("PYQTGRAPH_QT_LIB", "PyQt5")

import pyqtgraph as pg
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox

from .base_window import MonitorChildWindow
from .theme import DARK
from .utils import resolve_field_path

log = logging.getLogger(__name__)


class PlotWindow(MonitorChildWindow):
    """Window for plotting numeric message field over time."""

    SETTINGS_GROUP = "PlotWindow"
    MAX_SAMPLES = 50

    def __init__(self, spy, channel, field_name):
        super().__init__(settings_key=f"{channel}_{field_name}")
        self.spy = spy
        self.channel = channel
        self.field_name = field_name
        self.paused = False

        self.setWindowTitle(f"Plot - {self.channel}.{self.field_name}")
        self.setMinimumSize(600, 400)

        # Control panel
        control_layout = QHBoxLayout()

        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self._toggle_pause)
        control_layout.addWidget(self.pause_button)

        control_layout.addWidget(QLabel("Samples:"))
        self.samples_spinner = QSpinBox()
        self.samples_spinner.setRange(10, 1000)
        self.samples_spinner.setValue(self.MAX_SAMPLES)
        self.samples_spinner.valueChanged.connect(self._update_sample_size)
        control_layout.addWidget(self.samples_spinner)

        control_layout.addStretch()

        self.current_value_label = QLabel("Current: --")
        self.current_value_label.setStyleSheet(
            "font-weight: 600; font-size: 13px; background: transparent;"
        )
        control_layout.addWidget(self.current_value_label)

        # Plot — colors match the app palette
        self.plot_widget = pg.PlotWidget(background=DARK.surface)
        self.plot_widget.setTitle(f"{self.channel}.{self.field_name}", color=DARK.text)
        axis_color = QColor(DARK.text_muted)
        for axis in ("left", "bottom"):
            ax = self.plot_widget.getAxis(axis)
            ax.setPen(axis_color)
            ax.setTextPen(axis_color)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self.plot_widget.setLabel("left", "Value")
        self.plot_widget.setLabel("bottom", "Sample")

        self.data = deque(maxlen=self.MAX_SAMPLES)
        self.line = self.plot_widget.plot(pen=pg.mkPen(DARK.accent, width=2))

        layout = QVBoxLayout()
        layout.addLayout(control_layout)
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)

        self._start_timer(1000, self._refresh_data)
        self._restore_geometry()
        self.show()

    def _toggle_pause(self):
        self.paused = not self.paused
        self.pause_button.setText("Resume" if self.paused else "Pause")

    def _update_sample_size(self, value):
        self.data = deque(self.data, maxlen=value)

    def _refresh_data(self):
        if self.paused:
            return

        with self.spy.lock:
            msg = self.spy.msg.get(self.channel)

        if msg is None:
            return

        try:
            value = resolve_field_path(msg, self.field_name)
            self.data.append(value)
            self.line.setData(list(self.data))

            if isinstance(value, float):
                self.current_value_label.setText(f"Current: {value:.4f}")
            else:
                self.current_value_label.setText(f"Current: {value}")
        except (AttributeError, IndexError, ValueError):
            log.debug("Cannot access field '%s'", self.field_name)
