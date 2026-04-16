# LCM Network Monitor

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.7+](https://img.shields.io/badge/Python-3.7%2B-blue.svg)](https://python.org)
[![PyQt5](https://img.shields.io/badge/GUI-PyQt5-green.svg)](https://riverbankcomputing.com/software/pyqt/)

A lightweight, real-time network traffic monitor for [LCM (Lightweight Communications and Marshalling)](https://lcm-proj.github.io/). Built as a modern Python alternative to the Java-based `lcm-spy` tool.

![Main Window](screenshots/main_window.png)

## Features

- **Real-time traffic overview** — message counts, frequency (Hz), jitter, and auto-scaled bandwidth per channel
- **Automatic type detection** — discovers and loads LCM type definitions from Python packages with retry on failure
- **Message inspector** — recursive tree view of decoded message fields with search and copy support
- **Live plotting** — double-click any numeric field to plot its value over time
- **Dark theme** — professional UI with sortable tables, keyboard shortcuts, and persistent window geometry

## Quick Start

### Ubuntu/Debian

```bash
sudo apt install python3-pyqt5 python3-pyqtgraph liblcm-dev python3-lcm
git clone https://github.com/mbsm/lcm-monitor.git
cd lcm-monitor
pip3 install --user --break-system-packages .
```

### Other platforms

Install [LCM](https://lcm-proj.github.io/) for your system, then:

```bash
pip install PyQt5 pyqtgraph
pip install git+https://github.com/mbsm/lcm-monitor.git
```

### Run

```bash
lcm-monitor                   # installed command
python3 -m lcm_monitor        # or as a module
```

On Linux, a desktop launcher is created automatically on first run.

## Usage

### Command line options

```bash
lcm-monitor                                           # default multicast
lcm-monitor -u="udpm://239.255.76.67:7667?ttl=1"      # custom LCM URL
lcm-monitor -p=/path/to/lcmtypes/python               # load types on startup
```

### Main window

| Action | How |
|--------|-----|
| Sort by column | Double-click column header |
| Open inspector | Double-click a channel row |
| Import types | `Ctrl+I` or toolbar button |
| Clear statistics | `Ctrl+K` or toolbar button |
| Configure settings | Toolbar Properties button |

### Inspector window

| Action | How |
|--------|-----|
| Search fields | Type in the search bar |
| Copy value | Right-click a field |
| Plot a field | Double-click a numeric value |
| Close | `Escape` |

### Plot window

| Action | How |
|--------|-----|
| Pause / resume | Click the Pause button |
| Change window size | Adjust the Samples spinner (10 -- 1000) |
| Close | `Escape` |

## Screenshots

### Message Inspector

![Message Inspector](screenshots/inspector.png)

## Architecture

```
lcm_monitor/
├── lcm_network_monitor.py   # Main window and application entry point
├── lcm_spy.py               # Message handling, type detection, statistics
├── inspector_window.py       # Message inspector tree view
├── plot_window.py            # Real-time field plotting
├── base_window.py            # Shared child-window base class
├── channel_stats.py          # Per-channel statistics (Hz, bandwidth, jitter)
├── utils.py                  # Field path resolution, formatting, tree builder
└── styles.py                 # Dark theme stylesheet
```

**Key design decisions:**

- **Thread-safe** — LCM messages are handled on a background thread; the GUI polls at 1 Hz (configurable) under a shared lock
- **Generation-based change detection** — the table and inspector skip rebuilds when no new messages have arrived
- **Non-blocking type loading** — filesystem scanning and module imports happen outside the lock so the message handler is never stalled
- **Automatic type detection with retry** — each channel gets up to 5 decode attempts before being marked as undecodable, handling transient failures on startup
- **Zero heavyweight dependencies** — statistics are computed with pure Python (no NumPy required)

## Development

```bash
git clone https://github.com/mbsm/lcm-monitor.git
cd lcm-monitor
pip3 install -e .[dev]

# Generate test traffic (requires LCM types)
python3 tools/traffic_gen.py
```

See [INSTALL.md](INSTALL.md) for detailed platform-specific instructions.

## Author

Matias Bustos SM

## License

MIT License -- see [LICENSE](LICENSE) for details.
