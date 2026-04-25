"""LCM multicast sniffer that attributes traffic to source hosts.

Runs alongside :class:`LCMMessageSpy`: opens its own UDP socket joined to the
LCM multicast group so ``recvfrom`` exposes the source IP that the lcm Python
API hides. Parses just enough of the LCM2 wire format to extract the channel
name and the attributable byte count per packet — no message reassembly.
"""

import logging
import socket
import struct
import threading
import time
from collections import defaultdict
from urllib.parse import urlparse

from .channel_stats import ChannelStats
from .utils import format_bandwidth

log = logging.getLogger(__name__)

LCM_MAGIC_SHORT = 0x4C433032  # b"LC02"
LCM_MAGIC_LONG = 0x4C433033   # b"LC03"

SHORT_HEADER_LEN = 8   # magic + msg_seqno
LONG_HEADER_LEN = 20   # magic + seqno + msg_size + frag_offset + frag_no + frags_in_msg


def parse_endpoint(udpm_url, default_addr="239.255.76.67", default_port=7667):
    """Extract ``(multicast_addr, port)`` from a ``udpm://addr:port?ttl=N`` URL."""
    try:
        parsed = urlparse(udpm_url)
        return parsed.hostname or default_addr, parsed.port or default_port
    except ValueError:
        return default_addr, default_port


def parse_lcm_packet(data):
    """Decode an LCM UDP packet header.

    Returns ``(channel, attributable_size)`` for short messages and the first
    fragment of long messages. Returns ``None`` for later fragments and
    non-LCM packets — those aren't attributable to a channel without
    reassembly, so we skip them for per-channel accounting.
    """
    if len(data) < SHORT_HEADER_LEN:
        return None

    magic = struct.unpack_from("!I", data, 0)[0]

    if magic == LCM_MAGIC_SHORT:
        channel_end = data.find(b"\x00", SHORT_HEADER_LEN)
        if channel_end < 0:
            return None
        try:
            channel = data[SHORT_HEADER_LEN:channel_end].decode("ascii")
        except UnicodeDecodeError:
            return None
        return channel, len(data)

    if magic == LCM_MAGIC_LONG:
        if len(data) < LONG_HEADER_LEN:
            return None
        msg_size, _frag_offset, frag_no, _frags_in_msg = struct.unpack_from(
            "!IIHH", data, 8
        )
        # Only fragment 0 carries the channel name.
        if frag_no != 0:
            return None
        channel_end = data.find(b"\x00", LONG_HEADER_LEN)
        if channel_end < 0:
            return None
        try:
            channel = data[LONG_HEADER_LEN:channel_end].decode("ascii")
        except UnicodeDecodeError:
            return None
        return channel, msg_size

    return None


class HostStats:
    """Per-host aggregate counters."""

    __slots__ = ("first_seen", "last_seen", "msg_count", "total_bytes")

    def __init__(self):
        now = time.time()
        self.first_seen = now
        self.last_seen = now
        self.msg_count = 0
        self.total_bytes = 0


class HostSpy:
    """Sniffs LCM multicast traffic and aggregates per-host, per-channel stats."""

    ACTIVE_WINDOW_S = 2.0

    def __init__(self, udpm_url, n_samples):
        self.n_samples = n_samples
        self.host_stats = {}
        self.host_channels = defaultdict(dict)  # ip -> {channel: ChannelStats}
        self.lock = threading.Lock()
        self.generation = 0

        self.mc_addr, self.mc_port = parse_endpoint(udpm_url)
        self._sock = None
        self._thread = None
        self._running = False

    def start(self):
        """Open the multicast socket and start the reader thread.

        Returns False if the socket cannot be opened (port busy, no permission,
        no multicast interface). The GUI continues to work without host info.
        """
        try:
            self._sock = self._open_socket()
        except OSError as e:
            log.warning(
                "HostSpy: cannot join %s:%d (%s) — host attribution disabled",
                self.mc_addr, self.mc_port, e,
            )
            return False
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._running = False
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass

    def _open_socket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except OSError:
                pass
        sock.bind(("", self.mc_port))
        mreq = struct.pack(
            "4sl", socket.inet_aton(self.mc_addr), socket.INADDR_ANY
        )
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        sock.settimeout(0.5)
        return sock

    def _loop(self):
        while self._running:
            try:
                data, (ip, _port) = self._sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break
            self._record(ip, data)

    def _record(self, ip, data):
        parsed = parse_lcm_packet(data)
        now = time.time()
        with self.lock:
            stats = self.host_stats.get(ip)
            if stats is None:
                stats = HostStats()
                self.host_stats[ip] = stats
            stats.last_seen = now
            stats.msg_count += 1
            stats.total_bytes += len(data)

            if parsed is not None:
                channel, attrib_size = parsed
                channels = self.host_channels[ip]
                ch_stats = channels.get(channel)
                if ch_stats is None:
                    ch_stats = ChannelStats(self.n_samples)
                    channels[channel] = ch_stats
                ch_stats.update(attrib_size)
                self.generation += 1

    def set_sample_window(self, n_samples):
        with self.lock:
            self.n_samples = n_samples
            for channels in self.host_channels.values():
                for ch_stats in channels.values():
                    ch_stats.resize(n_samples)

    def clear(self):
        with self.lock:
            self.host_stats.clear()
            self.host_channels.clear()
            self.generation += 1

    def get_host_summary(self):
        """Snapshot of per-host stats sorted by IP.

        Returns ``(rows, generation)`` where each row is
        ``{"ip", "total_kbps", "msg_count", "channel_count", "active"}``.
        """
        now = time.time()
        rows = []
        with self.lock:
            for ip, stats in self.host_stats.items():
                channels = self.host_channels.get(ip, {})
                total_kbps = sum(c.bandwidth_kbps() for c in channels.values())
                rows.append({
                    "ip": ip,
                    "total_kbps": total_kbps,
                    "msg_count": stats.msg_count,
                    "channel_count": len(channels),
                    "active": (now - stats.last_seen) < self.ACTIVE_WINDOW_S,
                })
            gen = self.generation
        rows.sort(key=lambda r: tuple(int(p) for p in r["ip"].split(".") if p.isdigit()))
        return rows, gen

    def get_channel_rows(self, ip, channel_meta):
        """Build display rows for one host, joined with metadata from LCMMessageSpy.

        ``channel_meta`` maps ``channel -> (type_name, decodable_bool)`` so the
        Type / Decodable columns line up with the unfiltered view.
        """
        rows = []
        with self.lock:
            channels = list(self.host_channels.get(ip, {}).items())

        for channel, stats in channels:
            period = stats.period()
            hz = 1 / period if period > 0 else 0
            jitter_ms = stats.jitter() * 1000
            bw_kbps = stats.bandwidth_kbps()
            bw_value, bw_unit = format_bandwidth(bw_kbps)
            type_name, decodable = channel_meta.get(channel, ("Unknown", False))
            rows.append({
                "Channel": channel,
                "Type": type_name,
                "Num Msgs": stats.hits,
                "Hz": f"{hz:.2f}",
                "1/Hz": f"{period * 1000:.2f} ms",
                "Jitter": f"{jitter_ms:.2f} ms",
                "Bandwidth": f"{bw_value:.2f} {bw_unit}",
                "Decodable": "True" if decodable else "False",
            })
        return rows
