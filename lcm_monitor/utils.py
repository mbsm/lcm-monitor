"""
Utility functions for LCM Network Monitor.
"""

from PyQt5.QtWidgets import QTreeWidgetItem


def get_cmd_option(argv, option, default):
    """Parse command line option with format: -option=value."""
    for arg in argv:
        if arg.startswith(option):
            return arg[len(option):]
    return default


def format_bandwidth(kbps):
    """Format bandwidth value with auto-scaled units.

    Returns:
        Tuple of (value, unit_string)
    """
    if kbps >= 1024 * 1024:
        return kbps / (1024 * 1024), "GB/s"
    if kbps >= 1024:
        return kbps / 1024, "MB/s"
    return kbps, "KB/s"


def is_lcm_message(obj):
    """Check if an object is an LCM message type."""
    return hasattr(obj, '__slots__') and hasattr(obj, '__typenames__') and hasattr(obj, '__dimensions__')


def resolve_field_path(msg, field_path):
    """Navigate a dotted field path through an LCM message.

    Supports attribute access and array indexing (e.g. "pose.[0].x").

    Raises:
        AttributeError, IndexError, ValueError on invalid paths.
    """
    value = msg
    for part in field_path.split('.'):
        if part.startswith('[') and part.endswith(']'):
            value = value[int(part[1:-1])]
        else:
            value = getattr(value, part)
    return value


def fill_qtreeitem_with_lcm(tree_item, lcm_message):
    """Fills a QTreeWidgetItem with the fields of an LCM message."""
    for i, slot in enumerate(lcm_message.__slots__):
        typename = lcm_message.__typenames__[i]
        dimension = lcm_message.__dimensions__[i]
        value = getattr(lcm_message, slot)

        child_item = QTreeWidgetItem()
        child_item.setText(0, slot)

        if is_lcm_message(value):
            child_item.setText(2, typename)
            fill_qtreeitem_with_lcm(child_item, value)
        elif dimension is None:
            child_item.setText(1, str(value))
            child_item.setText(2, typename)
        else:
            child_item.setText(2, f"{typename}{dimension}")
            for j, elem in enumerate(value):
                elem_item = QTreeWidgetItem()
                elem_item.setText(0, f"[{j}]")
                if is_lcm_message(elem):
                    fill_qtreeitem_with_lcm(elem_item, elem)
                else:
                    elem_item.setText(1, str(elem))
                child_item.addChild(elem_item)

        tree_item.addChild(child_item)
