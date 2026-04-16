#!/usr/bin/env python3
"""Setup script for LCM Network Monitor.

Kept alongside pyproject.toml solely for the PostInstallCommand
that installs a .desktop file on Linux.
"""

from setuptools import setup, find_packages
from setuptools.command.install import install
import os
import sys
import shutil


class PostInstallCommand(install):
    """Post-installation: installs .desktop file on Linux."""

    def run(self):
        install.run(self)
        if sys.platform.startswith('linux'):
            self._install_desktop_file()

    def _install_desktop_file(self):
        try:
            if os.geteuid() == 0:
                desktop_dir = '/usr/share/applications'
            else:
                desktop_dir = os.path.expanduser('~/.local/share/applications')

            os.makedirs(desktop_dir, exist_ok=True)

            script_path = shutil.which('lcm-monitor') or 'lcm-monitor'

            desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=LCM Network Monitor
Comment=Monitor and visualize LCM network traffic in real-time
Exec={script_path}
Icon=network-workgroup
Terminal=false
Categories=Development;Network;Utility;
Keywords=LCM;Network;Monitor;Traffic;
"""
            desktop_file = os.path.join(desktop_dir, 'lcm-network-monitor.desktop')
            with open(desktop_file, 'w') as f:
                f.write(desktop_content)
            os.chmod(desktop_file, 0o755)

            print(f"\nDesktop file installed: {desktop_file}")
        except Exception as e:
            print(f"\nCould not install desktop file: {e}")
            print("  You can still run the application from terminal: lcm-monitor")


setup(
    name='lcm-network-monitor',
    version='1.0.0',
    author='Matias Bustos',
    author_email='matias.bustos.sm@outlook.com',
    description='Python-based LCM network traffic monitor (lcm-spy alternative)',
    packages=find_packages(),
    python_requires='>=3.7',
    install_requires=[
        'PyQt5>=5.15.0',
        'pyqtgraph>=0.12.0',
    ],
    entry_points={
        'console_scripts': [
            'lcm-monitor=lcm_monitor.lcm_network_monitor:main',
        ],
    },
    cmdclass={
        'install': PostInstallCommand,
    },
)
