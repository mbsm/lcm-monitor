"""
LCM Message Spy - Monitors LCM traffic and manages type detection.
"""

import os
import sys
import inspect
import importlib
import threading

from .channel_stats import ChannelStats
from .utils import get_cmd_option


class LCMMessageSpy:
    """Monitors LCM traffic, manages type detection, and aggregates statistics."""
    
    def __init__(self, n_samples):
        self.n_samples = n_samples
        self.stats = {}  # channel -> ChannelStats
        self.msg = {}  # channel -> decoded message
        self.types = []  # List of all known LCM message types
        self.channel_type = {}  # channel -> detected LCM message type
        self.lock = threading.Lock()
        
        # Load types from command line if specified
        path = get_cmd_option(sys.argv, "-p=", None)
        if path is not None:
            self.load_types(path)

    def load_types(self, path):
        """Load all LCM types from the specified directory.
        
        Args:
            path: Directory containing LCM type definitions
        """
        with self.lock:
            # Clear mappings so we re-detect types for all channels
            self.channel_type = {}
            self.msg = {}
            self.types = []
            
            abs_path = os.path.abspath(path)
            if not os.path.exists(abs_path):
                print(f"[!] Path does not exist: {abs_path}")
                return

            print(f"[*] Scanning for LCM types in: {abs_path}")
            
            # Add parent directory to sys.path to resolve package imports correctly
            parent_dir = os.path.dirname(abs_path)
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            
            package_name = os.path.basename(abs_path)
            
            # 1. Try to load the module as a package
            try:
                # If there's an __init__.py, import it
                init_file = os.path.join(abs_path, '__init__.py')
                if os.path.exists(init_file):
                    spec = importlib.util.spec_from_file_location(package_name, init_file)
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[package_name] = module
                    spec.loader.exec_module(module)
                    
                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj) and hasattr(obj, 'decode'):
                            self.types.append(obj)
            except Exception as e:
                print(f"[!] Error loading package {package_name}: {e}")

            # 2. Recursively find and import all submodules
            self._load_from_dir(abs_path, package_name)
            
            print(f"[*] Successfully loaded {len(self.types)} LCM types.")
            if len(self.types) > 0:
                print(f"[*] Sample types: {[t.__name__ for t in self.types[:5]]}...")

    def _load_from_dir(self, path, package_name):
        """Recursively load all LCM type classes from directory.
        
        Args:
            path: Root directory to search
            package_name: Python package name
        """
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith(".py") and file != "__init__.py":
                    # Convert file path to module path (e.g. pkg.subpkg.module)
                    rel_path = os.path.relpath(os.path.join(root, file), os.path.dirname(path))
                    module_name = rel_path.replace(os.path.sep, ".")[:-3]
                    
                    try:
                        # Use import_module to handle dependency resolution
                        m = importlib.import_module(module_name)
                        for name, obj in inspect.getmembers(m):
                            if inspect.isclass(obj) and hasattr(obj, 'decode'):
                                # Avoid duplicates
                                if obj not in self.types:
                                    self.types.append(obj)
                    except Exception as e:
                        # Silent failure for non-LCM files
                        pass

    def check_type(self, data):
        """Attempt to detect message type by trying to decode with all known types.
        
        Args:
            data: Raw LCM message data
            
        Returns:
            Matching LCM type class or None if no match found
        """
        for lcm_type in self.types:
            try:
                lcm_type.decode(data)
                return lcm_type
            except Exception:
                pass
        return None       

    def handle_message(self, channel, data):
        """Process incoming LCM message.
        
        Args:
            channel: LCM channel name
            data: Raw message data
        """
        with self.lock:
            if channel not in self.stats:
                self.stats[channel] = ChannelStats(self.n_samples)

            # Use len(data) for actual payload size, sys.getsizeof includes object overhead
            self.stats[channel].update(len(data))
            
            # If type is unknown or we just loaded new types, try to detect it
            # We retry if it's None to handle cases where messages arrive before types are loaded
            if self.channel_type.get(channel) is None:
                # To avoid heavy CPU usage, only retry periodically or if we have types
                # For now, let's retry if we have any types loaded
                if self.types:
                    lcmtype = self.check_type(data)
                    if lcmtype:
                        print(f"[*] Detected type for channel {channel}: {lcmtype.__name__}")
                        self.channel_type[channel] = lcmtype
            
            lcmtype = self.channel_type.get(channel)
            
            if lcmtype is not None:
                try:
                    self.msg[channel] = lcmtype.decode(data)
                except Exception as e:
                    # If decoding fails (maybe wrong type detected?), reset it
                    # print(f"Error decoding {channel}: {e}")
                    self.msg[channel] = None
            else:
                self.msg[channel] = None

    def total_traffic(self):
        """Calculate total network traffic across all channels.
        
        Returns:
            Tuple of (bandwidth_value, unit_string)
        """
        total_bw = 0
        with self.lock:
            for channel in self.stats:
                total_bw += self.stats[channel].bandwidth_kbps()

        # Auto-scale units
        if total_bw > 1024 * 1024:
            return total_bw / (1024 * 1024), "GB/s"
        elif total_bw > 1024:
            return total_bw / 1024, "MB/s"
        else:
            return total_bw, "KB/s"

    def traffic_data(self):
        """Generate table data for all monitored channels.
        
        Returns:
            List of dictionaries containing channel statistics
        """
        data = []
        with self.lock:
            channels = list(self.stats.keys())
            
            for channel in channels:
                stats = self.stats[channel]
                period = stats.period()
                hz = 1 / period if period > 0 else 0
                jitter_ms = stats.jitter() * 1000
                bandwidth = stats.bandwidth_kbps()
                
                # Auto-scale bandwidth units
                if bandwidth > 1024 * 1024:
                    bw_value, bw_unit = bandwidth / (1024 * 1024), "GB/s"
                elif bandwidth > 1024:
                    bw_value, bw_unit = bandwidth / 1024, "MB/s"
                else:
                    bw_value, bw_unit = bandwidth, "KB/s"
                
                lcm_type = self.channel_type.get(channel)
                type_name = lcm_type.__name__ if lcm_type else "Unknown"
                
                row = {
                    "Channel": channel,
                    "Type": type_name,
                    "Num Msgs": stats.hits,
                    "Hz": f"{hz:.2f}",
                    "1/Hz": f"{period * 1000:.2f} ms",
                    "Jitter": f"{jitter_ms:.2f} ms",
                    "Bandwidth": f"{bw_value:.2f} {bw_unit}",
                    "Decodable": "True" if self.msg.get(channel) else "False"
                }
                data.append(row)

        # Return empty row if no data
        if not data:
            data.append({
                "Channel": "", "Type": "", "Num Msgs": "", 
                "Hz": "", "1/Hz": "", "Jitter": "", 
                "Bandwidth": "", "Decodable": ""
            })
        return data

    def clear(self):
        """Clear all statistics and message data."""
        with self.lock:
            self.stats = {}
            self.msg = {}
            self.channel_type = {}
