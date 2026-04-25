"""
LCM Message Spy - Monitors LCM traffic and manages type detection.
"""

import os
import sys
import time
import inspect
import importlib
import logging
import threading
from collections import namedtuple

from .channel_stats import ChannelStats
from .utils import format_bandwidth

log = logging.getLogger(__name__)

COLUMNS = ["Channel", "Type", "Num Msgs", "Hz", "1/Hz", "Jitter", "Bandwidth", "Decodable"]
DECODABLE_COL = COLUMNS.index("Decodable")

DisplayData = namedtuple('DisplayData', [
    'rows', 'has_data', 'channel_count', 'active', 'total_bw', 'bw_unit', 'generation',
])


def sort_traffic_data(data, column, ascending=True):
    """Sort traffic data rows by column index."""
    if column >= len(COLUMNS):
        return data

    column_name = COLUMNS[column]
    sorted_data = list(data)

    if column_name == "Num Msgs":
        sorted_data.sort(key=lambda x: x.get(column_name, 0), reverse=not ascending)
    elif column_name in ("Hz", "1/Hz", "Jitter", "Bandwidth"):
        def extract_number(x):
            try:
                return float(str(x.get(column_name, "0")).split()[0])
            except (ValueError, IndexError):
                return 0.0
        sorted_data.sort(key=extract_number, reverse=not ascending)
    else:
        sorted_data.sort(key=lambda x: x.get(column_name, ""), reverse=not ascending)

    return sorted_data


class LCMMessageSpy:
    """Monitors LCM traffic, manages type detection, and aggregates statistics."""

    MAX_TYPE_CHECK_ATTEMPTS = 5

    def __init__(self, n_samples, types_path=None):
        self.n_samples = n_samples
        self.stats = {}
        self.msg = {}
        self.types = []
        self._type_names = set()
        self.channel_type = {}
        self._type_check_attempts = {}
        self.lock = threading.Lock()
        self.generation = 0

        if types_path is not None:
            self.load_types(types_path)

    def set_sample_window(self, n_samples):
        """Update the sample window size for all channels."""
        with self.lock:
            self.n_samples = n_samples
            for stats in self.stats.values():
                stats.resize(n_samples)

    def load_types(self, path):
        """Load all LCM types from the specified directory.

        Scanning and imports happen outside the lock to avoid blocking
        the LCM handler thread during file I/O.
        """
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            log.warning("Path does not exist: %s", abs_path)
            return

        log.info("Scanning for LCM types in: %s", abs_path)

        parent_dir = os.path.dirname(abs_path)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        package_name = os.path.basename(abs_path)
        new_types = []
        new_type_names = set()

        def register(cls):
            key = f"{cls.__module__}.{cls.__qualname__}"
            if key not in new_type_names:
                new_type_names.add(key)
                new_types.append(cls)

        try:
            init_file = os.path.join(abs_path, '__init__.py')
            if os.path.exists(init_file):
                spec = importlib.util.spec_from_file_location(package_name, init_file)
                module = importlib.util.module_from_spec(spec)
                sys.modules[package_name] = module
                spec.loader.exec_module(module)

                for _name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and hasattr(obj, 'decode'):
                        register(obj)
        except Exception as e:
            log.error("Error loading package %s: %s", package_name, e)

        for root, _dirs, files in os.walk(abs_path):
            for file in files:
                if file.endswith(".py") and file != "__init__.py":
                    rel_path = os.path.relpath(os.path.join(root, file), parent_dir)
                    module_name = rel_path.replace(os.path.sep, ".")[:-3]

                    try:
                        m = importlib.import_module(module_name)
                        for _name, obj in inspect.getmembers(m):
                            if inspect.isclass(obj) and hasattr(obj, 'decode'):
                                register(obj)
                    except Exception as e:
                        log.debug("Skipping %s: %s", module_name, e)

        log.info("Loaded %d LCM types", len(new_types))
        if new_types:
            log.info("Sample types: %s", [t.__name__ for t in new_types[:5]])

        with self.lock:
            self.channel_type.clear()
            self.msg.clear()
            self._type_check_attempts.clear()
            self.types = new_types
            self._type_names = new_type_names
            self.generation += 1

    def check_type(self, data):
        """Attempt to detect message type by trying to decode with all known types.

        Returns:
            Tuple of (matching_type, decoded_message) or (None, None)
        """
        for lcm_type in self.types:
            try:
                msg = lcm_type.decode(data)
                return lcm_type, msg
            except Exception:
                pass
        return None, None

    def handle_message(self, channel, data):
        """Process incoming LCM message."""
        with self.lock:
            if channel not in self.stats:
                self.stats[channel] = ChannelStats(self.n_samples)

            self.stats[channel].update(len(data))
            self.generation += 1

            if channel not in self.channel_type and self.types:
                attempts = self._type_check_attempts.get(channel, 0) + 1
                self._type_check_attempts[channel] = attempts
                lcm_type, msg = self.check_type(data)
                if lcm_type:
                    log.info("Detected type for %s: %s", channel, lcm_type.__name__)
                    self.channel_type[channel] = lcm_type
                    self.msg[channel] = msg
                    return
                if attempts >= self.MAX_TYPE_CHECK_ATTEMPTS:
                    self.channel_type[channel] = None

            lcm_type = self.channel_type.get(channel)
            if lcm_type is not None:
                try:
                    self.msg[channel] = lcm_type.decode(data)
                except Exception:
                    self.msg[channel] = None
            else:
                self.msg[channel] = None

    def get_display_data(self):
        """Get all display data under a single lock acquisition."""
        now = time.time()
        rows = []
        total_kbps = 0
        active = False

        with self.lock:
            channel_count = len(self.stats)
            gen = self.generation

            for channel, stats in self.stats.items():
                period = stats.period()
                hz = 1 / period if period > 0 else 0
                jitter_ms = stats.jitter() * 1000
                bw_kbps = stats.bandwidth_kbps()
                total_kbps += bw_kbps
                bw_value, bw_unit = format_bandwidth(bw_kbps)

                if stats.timestamps and (now - stats.timestamps[-1]) < 2.0:
                    active = True

                lcm_type = self.channel_type.get(channel)
                type_name = lcm_type.__name__ if lcm_type else "Unknown"

                rows.append({
                    "Channel": channel,
                    "Type": type_name,
                    "Num Msgs": stats.hits,
                    "Hz": f"{hz:.2f}",
                    "1/Hz": f"{period * 1000:.2f} ms",
                    "Jitter": f"{jitter_ms:.2f} ms",
                    "Bandwidth": f"{bw_value:.2f} {bw_unit}",
                    "Decodable": "True" if self.msg.get(channel) else "False"
                })

        total_bw, total_unit = format_bandwidth(total_kbps)
        return DisplayData(
            rows=rows, has_data=channel_count > 0, channel_count=channel_count,
            active=active, total_bw=total_bw, bw_unit=total_unit, generation=gen,
        )

    def get_channel_meta(self):
        """Snapshot ``{channel: (type_name, decodable_bool)}`` for joining with HostSpy rows."""
        with self.lock:
            return {
                ch: (
                    t.__name__ if t else "Unknown",
                    self.msg.get(ch) is not None,
                )
                for ch, t in self.channel_type.items()
            }

    def clear(self):
        """Clear all statistics and message data."""
        with self.lock:
            self.stats.clear()
            self.msg.clear()
            self.channel_type.clear()
            self._type_check_attempts.clear()
            self.generation += 1
