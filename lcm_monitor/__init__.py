"""
LCM Network Monitor - Real-time monitoring and visualization of LCM network traffic.

A Python-based alternative to the Java lcm-spy tool, providing modern PyQt5-based
visualization with dynamic type discovery and statistical analysis.
"""

__version__ = "1.0.0"
__author__ = "Matias Bustos"
__license__ = "MIT"

from .lcm_spy import LCMMessageSpy
from .inspector_window import MessageInspectorWindow
from .plot_window import PlotWindow
from .channel_stats import ChannelStats

__all__ = [
    "LCMMessageSpy",
    "MessageInspectorWindow", 
    "PlotWindow",
    "ChannelStats",
]
