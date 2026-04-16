# Installation Guide - LCM Network Monitor

## Prerequisites

1. **Python 3.7 or higher**
   ```bash
   python3 --version
   ```

2. **LCM (Lightweight Communications and Marshalling)**

   **Ubuntu/Debian:**
   ```bash
   sudo apt install liblcm-dev python3-lcm
   ```

   **macOS (Homebrew):**
   ```bash
   brew install lcm
   pip3 install lcm
   ```

   **Windows / From Source:**
   See [lcm-proj/lcm](https://github.com/lcm-proj/lcm) for build instructions.

## Ubuntu/Debian

### Quick install

```bash
sudo apt update
sudo apt install python3-pyqt5 python3-pyqtgraph liblcm-dev python3-lcm git

git clone https://github.com/mbsm/lcm-monitor.git
cd lcm-monitor
pip3 install --user .
```

Make sure `~/.local/bin` is in your PATH:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Desktop launcher (optional)

```bash
sudo cp lcm.png /usr/share/pixmaps/lcm-network-monitor.png

sudo tee /usr/share/applications/lcm-network-monitor.desktop > /dev/null << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=LCM Network Monitor
Comment=Monitor and visualize LCM network traffic
Exec=python3 -m lcm_monitor
Icon=/usr/share/pixmaps/lcm-network-monitor.png
Terminal=false
Categories=Development;Network;Utility;
Keywords=LCM;Network;Monitor;Traffic;
StartupNotify=true
EOF

sudo update-desktop-database /usr/share/applications/
```

## macOS

```bash
brew install lcm
pip3 install lcm PyQt5 pyqtgraph

git clone https://github.com/mbsm/lcm-monitor.git
cd lcm-monitor
pip3 install .
```

## Windows

```powershell
pip install PyQt5 pyqtgraph

git clone https://github.com/mbsm/lcm-monitor.git
cd lcm-monitor
pip install .
```

LCM must be built from source on Windows — see [lcm-proj/lcm](https://github.com/lcm-proj/lcm).

## Install from GitHub directly

```bash
pip3 install git+https://github.com/mbsm/lcm-monitor.git
```

## Running

```bash
# As a module
python3 -m lcm_monitor

# Or via the installed command
lcm-monitor

# With a custom LCM URL
lcm-monitor -u="udpm://239.255.76.67:7667?ttl=1"

# Load LCM types on startup
lcm-monitor -p=/path/to/lcm_types
```

## Uninstall

```bash
pip3 uninstall lcm-network-monitor
```

On Linux, remove the desktop file if you created one:
```bash
sudo rm /usr/share/applications/lcm-network-monitor.desktop
sudo rm /usr/share/pixmaps/lcm-network-monitor.png
sudo update-desktop-database /usr/share/applications/
```

## Troubleshooting

### "lcm-monitor: command not found"
- Ensure `~/.local/bin` (Linux/Mac) or Python Scripts directory (Windows) is in PATH
- Try running: `python3 -m lcm_monitor`

### "No module named 'lcm'"
- Install LCM Python bindings: `sudo apt install python3-lcm` or `pip3 install lcm`

### "No module named 'PyQt5'"
- Run: `pip3 install PyQt5`

### Desktop icon doesn't appear (Linux)
- Run: `update-desktop-database ~/.local/share/applications/`
- Log out and log back in

## Development

```bash
git clone https://github.com/mbsm/lcm-monitor.git
cd lcm-monitor
pip3 install -e .[dev]

pytest
black lcm_monitor/
```
