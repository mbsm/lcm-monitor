"""
Channel statistics tracker for LCM Network Monitor.
"""

import time
import numpy as np
from collections import deque


class ChannelStats:
    """Statistics tracker for an LCM channel."""
    
    def __init__(self, n_samples):
        self.hits = 0
        self.timestamps = deque(maxlen=n_samples)
        self.msg_bytes = deque(maxlen=n_samples)

    def update(self, num_bytes):
        """Update statistics with new message."""
        self.timestamps.append(time.time())
        self.msg_bytes.append(num_bytes)
        self.hits += 1

    def period(self):
        """Calculate average period between messages in seconds."""
        if len(self.timestamps) < 2:
            return 0
        dt = np.diff(self.timestamps)
        return np.mean(dt)

    def bandwidth_kbps(self):
        """Calculate bandwidth in KB/s."""
        if len(self.timestamps) < 2:
            return 0
        
        dt = self.timestamps[-1] - self.timestamps[0]
        if dt > 0:
            bytes_per_second = np.sum(self.msg_bytes) / dt
            return bytes_per_second / 1024  # Convert to KB/s
        return 0

    def jitter(self):
        """Calculate jitter in seconds."""
        if len(self.timestamps) < 2:
            return 0
        dt = np.diff(self.timestamps)
        return np.std(dt)
