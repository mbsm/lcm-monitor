from PyQt5.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

# Define the Python class and nested classes
class NestedClass:
    def __init__(self):
        self.nested_attr1 = 10
        self.nested_attr2 = "nested_value"

class MyClass:
    def __init__(self):
        self.attribute1 = "value1"
        self.attribute2 = 42
        self.nested = NestedClass()
        self.list_attr = [NestedClass(), NestedClass(), 5, "string"]

# Recursive function to add class attributes to the tree
def add_class_attributes(item, obj):
    for attr in dir(obj):
        if not callable(getattr(obj, attr)) and not attr.startswith("__"):
            value = getattr(obj, attr)
            if isinstance(value, (bool, int, float, str)):
                child_item = QTreeWidgetItem([f"{attr}: {value}"])
                item.addChild(child_item)
            elif isinstance(value, list):
                list_item = QTreeWidgetItem([attr])
                item.addChild(list_item)
                for i, elem in enumerate(value):
                    if isinstance(elem, (bool, int, float, str)):
                        list_item.addChild(QTreeWidgetItem([f"[{i}]: {elem}"]))
                    else:
                        elem_item = QTreeWidgetItem([f"[{i}]"])
                        list_item.addChild(elem_item)
                        add_class_attributes(elem_item, elem)
            elif isinstance(value, object):
                child_item = QTreeWidgetItem([attr])
                item.addChild(child_item)
                add_class_attributes(child_item, value)

# Create the application
app = QApplication([])

# Create the main window
window = QWidget()
layout = QVBoxLayout()

# Create the QTreeWidget
tree = QTreeWidget()
tree.setHeaderLabels(["Class Structure"])

# Add the class name as the root item
class_item = QTreeWidgetItem([MyClass.__name__])
tree.addTopLevelItem(class_item)

# Add class attributes as child items
add_class_attributes(class_item, MyClass())

# Add the tree to the layout and set the layout for the window
layout.addWidget(tree)
window.setLayout(layout)

# Show the window
window.show()

# Run the application
app.exec_()