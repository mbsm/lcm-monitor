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


def fill_qtreeitem_with_lcm(tree_item, lcm_message):
    """
    Fills a QTreeWidgetItem with the variables of an LCM message.
    
    :param tree_item: QTreeWidgetItem to be filled
    :param lcm_message: LCM message object
    """
    for i, slot in enumerate(lcm_message.__slots__):
        typename = lcm_message.__typenames__[i]
        dimension = lcm_message.__dimensions__[i]
        value = getattr(lcm_message, slot)
        
        child_item = QTreeWidgetItem()
        
        # Check if the value is another LCM message
        if hasattr(value, '__slots__') and hasattr(value, '__typenames__') and hasattr(value, '__dimensions__'):
            child_item.setText(0, f"{slot}")
            child_item.setText(2, typename)
            fill_qtreeitem_with_lcm(child_item, value)
        else:
            # Format the value based on its type and dimension
            if dimension == None:
                formatted_value = str(value)
                child_item.setText(0, f"{slot}")
                child_item.setText(1, f"{formatted_value}")
                child_item.setText(2, typename)
            else:
                child_item.setText(0, f"{slot}")
                child_item.setText(2, f"{typename}{dimension}")
                for j, elem in enumerate(value):
                    elem_item = QTreeWidgetItem()
                    if hasattr(elem, '__slots__') and hasattr(elem, '__typenames__') and hasattr(elem, '__dimensions__'):
                        fill_qtreeitem_with_lcm(elem_item, elem)
                    else:
                        formated_value = str(elem)
                        elem_item.setText(1, f"{elem}")
                        
                    child_item.addChild(elem_item)
        
        tree_item.addChild(child_item)
