# Installation Guide - LCM Network Monitor

## Ubuntu/Debian Installation

### 1. Install System Dependencies

```bash
sudo apt update
sudo apt install python3-pyqt5 python3-pyqtgraph liblcm-dev python3-lcm git
```

### 2. Clone Repository

```bash
git clone https://github.com/mbsm/lcm-monitor.git
cd lcm-monitor
```

### 3. Install Application

```bash
sudo pip3 install -e . --break-system-packages
```

This installs in editable mode, so code changes take effect immediately without reinstalling.

### 4. Install Desktop Launcher (Optional)

```bash
# Copy icon
sudo cp lcm.png /usr/share/pixmaps/lcm-network-monitor.png

# Create desktop entry
sudo tee /usr/share/applications/lcm-network-monitor.desktop > /dev/null << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=LCM Network Monitor
Comment=Monitor and visualize LCM network traffic
Exec=/usr/bin/python3 -m lcm_monitor
Icon=/usr/share/pixmaps/lcm-network-monitor.png
Terminal=false
Categories=Development;Network;Utility;
Keywords=LCM;Network;Monitor;Traffic;
StartupNotify=true
EOF

# Update desktop database
sudo update-desktop-database /usr/share/applications/
```

### 5. Run the Application

From terminal:
```bash
python3 -m lcm_monitor
```

Or search for "LCM Network Monitor" in your application menu.

### Uninstall

```bash
sudo pip3 uninstall lcm-network-monitor --break-system-packages
sudo rm /usr/share/applications/lcm-network-monitor.desktop
sudo rm /usr/share/pixmaps/lcm-network-monitor.png
sudo update-desktop-database /usr/share/applications/
```

## Prerequisites (All Platforms)
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
   ```bash
   # See: https://github.com/lcm-proj/lcm
   git clone https://github.com/lcm-proj/lcm.git
   cd lcm
   mkdir build && cd build
   cmake ..
   make
   sudo make install
   ```

## Installation Methods

### Option 1: Install from Source (Recommended)

```bash
# Clone the repository
git clone https://github.com/mbsm/lcm-monitor.git
cd lcm_monitor

# Install in development mode (changes reflected immediately)
pip3 install -e .

# OR install normally
pip3 install .
```

### Option 2: Install from PyPI (when published)

```bash
pip3 install lcm-network-monitor
```

### Option 3: Install from GitHub directly

```bash
pip3 install git+https://github.com/mbsm/lcm-monitor.git
```

## Platform-Specific Notes

### 🐧 Linux (Ubuntu/Debian)

**System-wide installation (requires sudo):**
```bash
sudo pip3 install .
```
This will:
- Install to `/usr/local/`
- Create desktop entry in `/usr/share/applications/`
- Add `lcm-monitor` command to PATH

**User installation (no sudo):**
```bash
pip3 install --user .
```
This will:
- Install to `~/.local/`
- Create desktop entry in `~/.local/share/applications/`
- Command available as `~/.local/bin/lcm-monitor`

**Make sure `~/.local/bin` is in your PATH:**
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### 🪟 Windows

```powershell
# Install
pip install .

# Run
lcm-monitor

# Or use pythonw to avoid console window
pythonw -m lcm_monitor
```

**Create Desktop Shortcut:**
- Right-click Desktop → New → Shortcut
- Location: `C:\PythonXX\Scripts\lcm-monitor.exe` (or wherever Python is installed)
- Name: "LCM Network Monitor"

### 🍎 macOS

```bash
# Install
pip3 install .

# Run
lcm-monitor
```

**Add to Applications folder:**
```bash
# Create app launcher script
echo '#!/bin/bash' > ~/Applications/lcm-monitor.command
echo 'lcm-monitor' >> ~/Applications/lcm-monitor.command
chmod +x ~/Applications/lcm-monitor.command
```

## Verifying Installation

```bash
# Check if installed
pip3 show lcm-network-monitor

# Run the application
lcm-monitor

# Run with custom LCM URL
lcm-monitor -u=udpm://239.255.76.67:7667?ttl=1

# Load LCM types on startup
lcm-monitor -p=/path/to/lcm_types
```

## Uninstallation

```bash
pip3 uninstall lcm-network-monitor
```

On Linux, manually remove desktop file if needed:
```bash
rm ~/.local/share/applications/lcm-network-monitor.desktop
# or
sudo rm /usr/share/applications/lcm-network-monitor.desktop
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
- Manually update desktop database: `update-desktop-database ~/.local/share/applications/`
- Log out and log back in

## Development Installation

For contributors:

```bash
# Clone repository
git clone https://github.com/mbsm/lcm-monitor.git
cd lcm_monitor

# Install in editable mode with development dependencies
pip3 install -e .[dev]

# Run tests (if available)
pytest

# Format code
black lcm_monitor/
```
