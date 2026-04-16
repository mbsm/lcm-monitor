"""
Channel statistics tracker for LCM Network Monitor.
"""

import time
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

    def resize(self, n_samples):
        """Resize the sample window, preserving existing data."""
        self.timestamps = deque(self.timestamps, maxlen=n_samples)
        self.msg_bytes = deque(self.msg_bytes, maxlen=n_samples)

    def period(self):
        """Calculate average period between messages in seconds."""
        n = len(self.timestamps)
        if n < 2:
            return 0
        return (self.timestamps[-1] - self.timestamps[0]) / (n - 1)

    def bandwidth_kbps(self):
        """Calculate bandwidth in KB/s."""
        if len(self.timestamps) < 2:
            return 0
        dt = self.timestamps[-1] - self.timestamps[0]
        if dt > 0:
            return sum(self.msg_bytes) / dt / 1024
        return 0

    def jitter(self):
        """Calculate jitter (std deviation of period) in seconds."""
        n = len(self.timestamps)
        if n < 2:
            return 0
        ts = self.timestamps
        diffs = [ts[i + 1] - ts[i] for i in range(n - 1)]
        mean = sum(diffs) / len(diffs)
        variance = sum((d - mean) ** 2 for d in diffs) / len(diffs)
        return variance ** 0.5
