#!/usr/bin/env python3
"""
LCM Network Monitor - Main entry point

Run with: python3 -m lcm_monitor
Or: python3 run.py
"""

import sys
from PyQt5.QtWidgets import QApplication

# Set application metadata BEFORE any imports that might use QSettings
app = QApplication(sys.argv)
app.setOrganizationName("LCMMonitor")
app.setApplicationName("LCM Network Monitor")

# Now safe to import modules that use QSettings
from lcm_monitor.lcm_network_monitor import main as run_main
from lcm_monitor.styles import APP_STYLESHEET

app.setStyleSheet(APP_STYLESHEET)

if __name__ == '__main__':
    run_main(app)
