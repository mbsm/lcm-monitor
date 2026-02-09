# LCM Network Monitor

A performance-oriented real-time monitoring and visualization tool for [LCM (Lightweight Communications and Marshalling)](https://lcm-proj.github.io/) network traffic.

## Features

- **Real-time Traffic Overview**: Monitor channel names, message types, frequencies (Hz), jitter, and bandwidth usage
- **Dynamic Type Discovery**: Automatically discover and load LCM message types from Python modules at runtime
- **Recursive Inspector**: Deeply inspect nested LCM message structures using a tree view
- **Live Plotting**: Visualize numeric fields from LCM messages in real-time
- **Thread-Safe Architecture**: Decoupled network handling and UI rendering for high-performance monitoring
- **Professional UI**: Dark theme, toolbar, keyboard shortcuts, sortable tables, and more

## Background & Motivation

This project is a partial Python-based port of the original [lcm-spy](https://lcm-proj.github.io/group__LcmPy__lcm__spy.html) utility. It was developed to provide a lightweight, pure-Python alternative when environment updates caused compatibility issues with the standard Java-based implementation.

While inspired by the excellent work of the original LCM project authors, this tool focuses on providing a modern, Pythonic debugging experience using PyQt5 and pyqtgraph.

## Project Structure

```
lcm_monitor/
├── lcm_monitor/              # Main package
│   ├── __init__.py           # Package initialization  
│   ├── __main__.py           # Module entry point
│   ├── lcm_network_monitor.py # Main window
│   ├── lcm_spy.py            # LCM message spy & type detection
│   ├── inspector_window.py   # Message inspector UI
│   ├── plot_window.py        # Real-time plotting
│   ├── channel_stats.py      # Statistics tracking
│   ├── styles.py             # UI theme
│   └── utils.py              # Utility functions
├── run.py                    # Standalone entry point
├── test.py                   # Traffic simulator
├── setup.py                  # Installation script
├── README.md                 # This file
└── LICENSE                   # MIT License
```

## Installation

### Dependencies

- Python 3.6+
- `lcm` - LCM Python bindings
- `PyQt5` - GUI framework
- `pyqtgraph` - Plotting library
- `numpy` - Numerical computing

Install Python dependencies:
```bash
pip install PyQt5 pyqtgraph numpy
```

*Note: `lcm` must be installed separately according to the [LCM documentation](https://lcm-proj.github.io/).*

## Usage

### Running the Monitor

**Recommended: As a Python module**
```bash
python3 -m lcm_monitor
```

**Alternative: Using run.py**
```bash
python3 run.py
```

### Command Line Options

**Specify LCM URL:**
```bash
python3 -m lcm_monitor -u="udpm://239.255.76.67:7667?ttl=1"
```

**Load LCM Types:**
```bash
python3 -m lcm_monitor -p=/path/to/lcmtypes/python
```

Or use **File > Import LCM Types** from the menu.

### Testing

Generate sample LCM traffic:
```bash
python3 test.py
```

*(Note: Adjust `sys.path` in `test.py` for your LCM types.)*

## Features Guide

### Main Window
- **Toolbar**: Quick access to Import Types, Clear Statistics, Properties
- **Table**: Click column headers to sort (double-click toggles order)
- **Status Bar**: Connection indicator, channel count, total bandwidth
- **Empty State**: Shows helpful message when no messages received

### Inspector Window  
- **Search**: Filter fields in real-time
- **Type Column**: Shows LCM type information
- **Context Menu**: Right-click to copy values or field names
- **Double-Click**: Opens plot window for numeric fields
- **Escape**: Close window

### Plot Window
- **Pause/Resume**: Freeze plot to examine data
- **Sample Size**: Adjust history window (10-1000 samples)
- **Current Value**: Displays latest value
- **Escape**: Close window

### Keyboard Shortcuts
- `Ctrl+I` - Import LCM Types
- `Ctrl+K` - Clear Statistics  
- `Ctrl+Q` - Exit Application
- `Escape` - Close inspector/plot windows

## Architecture

- **Thread Safety**: `LCMMessageSpy.lock` protects shared data access
- **Event Loop**: Background daemon thread handles LCM with 100ms timeout
- **Dynamic Typing**: Recursive type discovery with retry on new imports
- **Performance**: Polling at 1Hz, high-frequency LCM in separate thread
- **Persistence**: Window geometry saved via `QSettings`

## Author

**Matias Bustos**

## License

MIT License - see [LICENSE](LICENSE) file for details.
