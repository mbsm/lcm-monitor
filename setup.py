#!/usr/bin/env python3
"""Setup script for LCM Network Monitor."""

from setuptools import setup, find_packages
from setuptools.command.install import install
import os
import sys
import shutil

# Read long description from README
try:
    with open('README.md', 'r', encoding='utf-8') as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = 'LCM Network Traffic Monitor - Real-time visualization tool'

# Read version from the main module
VERSION = '1.0.0'


class PostInstallCommand(install):
    """Post-installation for installation mode."""
    
    def run(self):
        install.run(self)
        
        # Only attempt desktop file installation on Linux
        if sys.platform.startswith('linux'):
            self.install_desktop_file()
    
    def install_desktop_file(self):
        """Install .desktop file on Linux systems."""
        try:
            # Determine installation directory
            if os.geteuid() == 0:  # Running as root/sudo
                desktop_dir = '/usr/share/applications'
            else:
                desktop_dir = os.path.expanduser('~/.local/share/applications')
            
            # Create directory if it doesn't exist
            os.makedirs(desktop_dir, exist_ok=True)
            
            # Find the installed script location
            script_path = shutil.which('lcm-monitor')
            if not script_path:
                script_path = 'lcm-monitor'  # Fallback
            
            # Create desktop file content
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
            
            # Make it executable
            os.chmod(desktop_file, 0o755)
            
            print(f"\n✓ Desktop file installed: {desktop_file}")
            print("  LCM Network Monitor should now appear in your application menu")
            
        except Exception as e:
            print(f"\n⚠ Could not install desktop file: {e}")
            print("  You can still run the application from terminal: lcm-monitor")


setup(
    name='lcm-network-monitor',
    version=VERSION,
    author='Your Name',
    author_email='your.email@example.com',
    description='Real-time LCM network traffic monitor and visualizer',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/lcm_monitor',
    py_modules=['lcm_network_monitor', 'test'],
    python_requires='>=3.7',
    install_requires=[
        'numpy>=1.20.0',
        'PyQt5>=5.15.0',
        'pyqtgraph>=0.12.0',
        # Note: LCM needs to be installed separately as it's not on PyPI
        # Users should install via: sudo apt install liblcm-dev python3-lcm
        # or build from source: https://github.com/lcm-proj/lcm
    ],
    extras_require={
        'dev': [
            'pytest>=6.0',
            'black',
            'flake8',
        ],
    },
    entry_points={
        'console_scripts': [
            'lcm-monitor=lcm_network_monitor:main',
            'lcm-test=test:main',
        ],
    },
    cmdclass={
        'install': PostInstallCommand,
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: System :: Monitoring',
        'Topic :: System :: Networking :: Monitoring',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Operating System :: OS Independent',
        'Environment :: X11 Applications :: Qt',
    ],
    keywords='lcm network monitor traffic visualization robotics',
    project_urls={
        'Bug Reports': 'https://github.com/yourusername/lcm_monitor/issues',
        'Source': 'https://github.com/yourusername/lcm_monitor',
    },
)
