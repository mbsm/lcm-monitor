#!/usr/bin/env python3
"""
LCM Network Monitor - Main entry point

Run with: python3 -m lcm_monitor
Or: python3 run.py
"""

import sys


def main():
    from PyQt5.QtWidgets import QApplication
    from lcm_monitor.lcm_network_monitor import main as run_main
    from lcm_monitor.styles import APP_STYLESHEET

    app = QApplication(sys.argv)
    app.setOrganizationName("LCMMonitor")
    app.setApplicationName("LCM Network Monitor")
    app.setStyleSheet(APP_STYLESHEET)

    run_main(app)


if __name__ == '__main__':
    main()
