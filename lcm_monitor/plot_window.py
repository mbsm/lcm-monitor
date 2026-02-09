"""
Plot Window - Real-time visualization of LCM message fields.
"""

from collections import deque

import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QSpinBox
)
from PyQt5.QtCore import QTimer, Qt, QSettings


class PlotWindow(QWidget):
    """Window for plotting numeric message field over time."""
    
    MAX_SAMPLES = 50
    UPDATE_RATE_MS = 1000
    
    def __init__(self, spy, channel, field_name):
        super().__init__()
        self.spy = spy
        self.channel = channel
        self.field_name = field_name
        self.paused = False
        self.max_samples = self.MAX_SAMPLES
        
        self.setWindowTitle(f"Plot - {self.channel}.{self.field_name}")
        self.setMinimumSize(600, 400)
        
        # Control panel
        control_layout = QHBoxLayout()
        
        self.pause_button = QPushButton("⏸ Pause")
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
        self.current_value_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        control_layout.addWidget(self.current_value_label)
        
        # Setup plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setTitle(f"{self.channel}.{self.field_name}")
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setLabel('left', 'Value')
        self.plot_widget.setLabel('bottom', 'Sample')
        
        self.data = deque(maxlen=self.max_samples)
        self.line = self.plot_widget.plot(pen='y')

        layout = QVBoxLayout()
        layout.addLayout(control_layout)
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(self.UPDATE_RATE_MS)
        self.show()
        
        # Restore window geometry after show
        settings = QSettings("LCMMonitor", "PlotWindow")
        geometry = settings.value(f"geometry_{self.channel}_{self.field_name}", None)
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
        settings = QSettings("LCMMonitor", "PlotWindow")
        settings.setValue(f"geometry_{self.channel}_{self.field_name}", self.saveGeometry())
        event.accept()
    
    def _toggle_pause(self):
        """Toggle pause/resume of plot updates."""
        self.paused = not self.paused
        if self.paused:
            self.pause_button.setText("▶ Resume")
        else:
            self.pause_button.setText("⏸ Pause")
    
    def _update_sample_size(self, value):
        """Update the maximum number of samples to display."""
        self.max_samples = value
        # Create new deque with updated size and copy old data
        old_data = list(self.data)
        self.data = deque(old_data, maxlen=self.max_samples)

    def update(self):
        """Update plot with latest field value."""
        if self.paused:
            return
            
        with self.spy.lock:
            msg = self.spy.msg.get(self.channel)
        
        if msg is None:
            return

        if hasattr(msg, self.field_name):
            value = getattr(msg, self.field_name)
            self.data.append(value)
            self.line.setData(list(self.data))
            
            # Update current value label
            if isinstance(value, float):
                self.current_value_label.setText(f"Current: {value:.4f}")
            else:
                self.current_value_label.setText(f"Current: {value}")
        else:
            print(f"Message no longer has attribute: {self.field_name}")
