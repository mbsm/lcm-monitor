#!/usr/bin/env python3

from collections import deque
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

import lcm
import sys
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore
import time
import threading
import numpy as np
import inspect


from pathlib import Path
home = str(Path.home())
import os
import importlib


def getCmdOption(argv, option, default):
    cmd = default
    for arg in argv:
        found = arg.find(option)
        if(found == 0): # at the begining 
            cmd = arg[len(option):] #from len to end
    return cmd


class ChannelStats():
    def __init__(self, n_samples):
        self.hits = 0
        self.timestamps = deque(maxlen=n_samples)
        self.msg_bytes = deque(maxlen=n_samples)
        self.msg = None

    def update(self, bytes):
        self.timestamps.append(time.time())
        self.msg_bytes.append(bytes)
        self.hits += 1

    def period(self):
        dt = np.diff(self.timestamps)
        if len(dt) == 0:
            return 0
        return np.mean(dt)

    def Kbps(self):
        dt = self.timestamps[-1] - self.timestamps[0]
        bytes_per_second = np.sum(self.msg_bytes)

        if (dt > 0):
            bytes_per_second = bytes_per_second/dt
        else:
            bytes_per_second = 0

        return bytes_per_second/1024 # KB/s

    def jitter(self):
        dt = np.diff(self.timestamps)
        return np.std(dt)


class Spy():
    def __init__(self, n_samples):
        self.n = n_samples
        self.stats = {}
        self.msg = {}
        self.types = []# dict of all lcm messages type known to the spy
        self.channel_type = {} #detected lcm msssges type for each channel
        path = getCmdOption(sys.argv, "-p=", None)
        if path is not None:            
            self.load_types(path)

    def load_types(self, path):
        #import all lcm types in the path

        #clear all so we can reload
        self.channel_type = {}
        self.stats = {}
        print("Loading LCM types from: ", path)
        module_path = path + '/'+'__init__.py'
        #module name is the name of the folder
        module_name = path.split('/')[-1]

        spec = importlib.util.spec_from_file_location(module_name, module_path )
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        #get all the classes in the module
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj):
                self.types.append(obj)

    def check_type(self, msg):
        for t in self.types:
            try :
                t.decode(msg)
                return t
            except:
                pass
        return None       

    def handleMsg(self, channel, data):
        #update stats of the msg
        if (channel not in self.stats.keys()):
            self.stats[channel] = ChannelStats(self.n)

        self.stats[channel].update(sys.getsizeof(data))
        
        #check if msg type is known
        if channel not in self.channel_type.keys():
            lcmtype = self.check_type(data)
            self.channel_type[channel] = lcmtype
        
        lcmtype = self.channel_type[channel]
        
        if lcmtype is not None:
            self.msg[channel] = lcmtype.decode(data)
        else:
            self.msg[channel] = None

    def total_traffic(self):
        total_bw = 0
        for channel in self.stats:
            bw = self.stats[channel].Kbps()
            total_bw += bw

        bw_unit = "KB/s"
        if (total_bw > 1024):
            total_bw = total_bw/1024
            bw_unit = "MB/s"
        
        if (total_bw > 1024*1024):
            total_bw = total_bw/1024/1024
            bw_unit = "GB/s"
        return total_bw, bw_unit

    def traffic_data(self):
        #generate the data for the table
        total_bw = 0
        data = []
        for channel in self.stats:
            ch = {}
            n = self.stats[channel].hits
            ts = self.stats[channel].period()
            
            if ts == 0:
                hz = 0
            else:
                hz = 1/ts

            jitter = self.stats[channel].jitter()
            bw = self.stats[channel].Kbps()
            total_bw += bw
            bw_unit = "KB/s"
            if (bw > 1024):
                bw = bw/1024
                bw_unit = "MB/s"
            if (bw > 1024*1024):
                bw = bw/1024/1024
                bw_unit = "GB/s"

            ch["Channel"] = channel
            ch["Type"] = self.channel_type[channel].__class__.__name__
            ch["Num Msgs"] = n
            ch["Hz"] = "{:.2f}".format(hz)
            ch["1/Hz"] = "{:.2f} ms".format(ts*1000)
            ch["Jitter"] = "{:.2f} ms".format(jitter*1000)
            ch["Bandwidth"] = "{:.2f} {}".format(bw, bw_unit)

            if self.msg[channel] is None:
                ch["Decodable"] = "False"
            else:
                ch["Decodable"] = "True"
            data.append(ch)

        if len(data) < 1:
            ch = {}
            ch["Channel"] = ""
            ch["Type"] = ""
            ch["Num Msgs"] = ""
            ch["Hz"] = ""
            ch["1/Hz"] = ""
            ch["Jitter"] = ""
            ch["Bandwidth"] = ""
            ch["Decodable"] = ""
            data.append(ch)
        return data

    def clear(self):
        self.stats = {}
        self.msg = {}


# function to fill a QtreeItem with childs from a lcm message object

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
            child_item.setText(0, f"{slot} ({typename}):")
            fill_qtreeitem_with_lcm(child_item, value)
        else:
            # Format the value based on its type and dimension
            if dimension == None:
                formatted_value = str(value)
                child_item.setText(0, f"{slot}")
                child_item.setText(1, f"{formatted_value}")
            else:
                child_item.setText(0, f"{slot} {dimension}:")
                for j, elem in enumerate(value):
                    elem_item = QTreeWidgetItem()
                    if hasattr(elem, '__slots__') and hasattr(elem, '__typenames__') and hasattr(elem, '__dimensions__'):
                        fill_qtreeitem_with_lcm(elem_item, elem)
                    else:
                        formated_value = str(elem)
                        elem_item.setText(1, f"{elem}")
                        
                    child_item.addChild(elem_item)
        
        tree_item.addChild(child_item)


class Window2(QWidget):                         
    def __init__(self, channel, spy):
        super().__init__()
        self.setStyleSheet('background-color: #333333; color: #d3d3d3;')
        self.channel = channel
        self.spy = spy
        self.setWindowTitle(self.channel)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Variable", "Value"])
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.itemDoubleClicked.connect(self.plot_window)
        
        layout = QVBoxLayout()
        layout.addWidget(self.tree)
        self.setLayout(layout)
        
        
        # update the tree widget with the info of the message every second
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(1000)

        self.show()

    def plot_window(self):
        # on double click, open a new window with a plot of the selected variable of the message, update every second and plot the last 50 samples
        item = self.tree.currentItem()
        varname = item.text(0)

        if varname == self.channel:
            return
        
        msg = self.spy.msg[self.channel]
        if msg is None:
            return
        
        if hasattr(msg, varname):
            self.plot = PlotWindow(self.spy, self.channel, varname)
        else:
            print("No such attribute")
   
    def update(self):
        # update the tree widget with the info of the message
        self.tree.clear()
        msg = self.spy.msg[self.channel]
        if msg is None:
            return
        
        root_item = self.tree.invisibleRootItem()
        fill_qtreeitem_with_lcm(root_item, msg)
        self.tree.expandAll()




                
        
class PlotWindow(QWidget):
    def __init__(self, spy, channel, varname):
        super().__init__()
        self.spy = spy
        self.channel = channel
        self.varname = varname
        self.setWindowTitle(f"{self.channel} - {self.varname}")
        self.setStyleSheet('background-color: #333333; color: #d3d3d3;')
        self.plot = pg.PlotWidget()
        self.plot.setTitle(f"{self.channel} - {self.varname}")
        self.plot.showGrid(x=True, y=True)
        self.plot.setLabel('left', 'Value')
        self.plot.setLabel('bottom', 'Time')
        self.plot.setLimits(xMin=0, xMax=50, yMin=-100, yMax=100)

        self.plot.show()

        self.data = deque(maxlen=50)
        self.data.append(0)
        self.time = deque(maxlen=50)
        self.time.append(time.time())

        # Get a line reference to update the plot
        self.line = self.plot.plot(pen='y')


        layout = QVBoxLayout()
        layout.addWidget(self.plot)
        self.setLayout(layout)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(1000)
        self.show()

    def update(self):
        # update the plot with the last 50 samples of the variable
        msg = self.spy.msg[self.channel]
        if msg is None:
            return

        if hasattr(msg, self.varname):
            self.data.append(getattr(msg, self.varname)) # append the new value to the data
            self.time.append(time.time()) # append the current time to the time
            #update the plot with the new data
            self.line.setData(self.data)

        else:
            print("No such attribute")


class Window(QMainWindow):
    def __init__(self, udpm):
        super().__init__()

                #properties
        self.udpm = udpm                
        self.update_rate = 1000
        self.n_samples = 30


        self.lc = lcm.LCM(self.udpm)
        self.spy = Spy(self.n_samples)
        self.running = True
        self.subscription = self.lc.subscribe(".*", self.spy.handleMsg)
        self.top = 500
        self.left = 200
        self.width = 800
        self.height = 400
        self.title ="LCM Network Traffic Monitor   " + udpm
        self.setStyleSheet('background-color: #333333; color: #d3d3d3;')

        self.main_window()
        self.windows={}
                    
        self.thread = threading.Thread(target=self.run, args=())
        self.thread.daemon = True  # Daemonize thread
        self.thread.start()        # Start

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_main_window)
        self.timer.start(self.update_rate)
        self.show()

    def main_window(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.top, self.left, self.width, self.height)

        self.table1 = pg.TableWidget()
        self.table1.verticalHeader().setVisible(False)
        self.table1.cellClicked.connect(self.msg_window)
        self.table1.setData(self.spy.traffic_data())
        self.setCentralWidget(self.table1)
        self.initMenu()
        self.status_bar = self.statusBar()
        self.status_bar.showMessage('Ready', 5000)

        # add a permanent widget to the status bar
        self.character_count = QLabel("Total Network LCM Traffic: {:.2f} {}".format(0, "KB/s"))
        self.status_bar.addPermanentWidget(self.character_count)
     
    def initMenu(self):
        # File menu actions
        # Create new action
        openAction = QAction(QIcon('open.png'), 'Import lcmtypes', self)
        openAction.setShortcut('  ')     
        openAction.setStatusTip('Open document')
        openAction.triggered.connect(self.open)

        propertyAction = QAction(QIcon('property.png'), 'Properties', self)
        propertyAction.setShortcut('  ')
        propertyAction.setStatusTip('Properties')
        propertyAction.triggered.connect(self.editPorperties)

        # Create exit action
        exitAction = QAction(QIcon('exit.png'), 'Exit', self)        
        exitAction.setShortcut('  ')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(self.close)
        
        #Clear Action
        clearAction = QAction(QIcon('clear.png'), 'Clear', self)
        clearAction.setShortcut('  ')
        clearAction.setStatusTip('Clear data')
        clearAction.triggered.connect(self.clear)

         # Create menu bar and add action
        menuBar = self.menuBar()
        fileMenu = menuBar.addMenu('File')
        fileMenu.addAction(openAction)
        fileMenu.addAction(propertyAction)
        fileMenu.addAction(exitAction)
        fileMenu.addAction(clearAction)
    
    def open(self):
        path = QFileDialog.getExistingDirectory(parent=self, caption='Select Folder',options=QFileDialog.ShowDirsOnly)
        if(path == ""):
            return
        self.spy.load_types(path)
            
    
    def close(self):
        self.running = False
        qApp.quit()
        
    def clear(self):
        self.spy.clear()
       

    def msg_window(self, row, col):                               
        item = self.table1.item(row, 0)
        channel = item.text()
        #if channel not in self.windows.keys():
        w = Window2(channel, self.spy)
        self.windows[channel]=w
        
    def update_main_window(self):
        self.table1.setData(self.spy.traffic_data())
        total_bw, bw_unit = self.spy.total_traffic()
        self.character_count.setText("Total Network LCM Traffic: {:.2f} {}".format(total_bw, bw_unit))
        self.table1.horizontalHeader().setStretchLastSection(True)

    def editPorperties(self):
        # form window to edit the udpm value, refresh rate, and the number of samples

        self.form = QDialog()
        self.form.setWindowTitle("Properties")
        self.form.setGeometry(100, 100, 200, 200)
        layout = QVBoxLayout()
        self.form.setLayout(layout)

        # add a label and a line edit for the udpm value
        self.udpm_label = QLabel("UDPM:")
        layout.addWidget(self.udpm_label)
        self.udpm_edit = QLineEdit()
        self.udpm_edit.setText(self.udpm)
        layout.addWidget(self.udpm_edit)

        # add a label and a line edit for the refresh rate
        self.refresh_label = QLabel("Refresh rate (ms):")
        layout.addWidget(self.refresh_label)
        self.refresh_edit = QLineEdit()
        self.refresh_edit.setText(str(self.update_rate))
        layout.addWidget(self.refresh_edit)

        # add a label and a line edit for the number of samples
        self.samples_label = QLabel("Number of samples:")
        layout.addWidget(self.samples_label)
        self.samples_edit = QLineEdit()
        self.samples_edit.setText(str(self.n_samples))
        layout.addWidget(self.samples_edit)

        def save():
            # save the changes
            self.udpm = self.udpm_edit.text()
            self.update_rate = int(self.refresh_edit.text())
            self.n_samples = int(self.samples_edit.text())
            self.form.close()


        # add a button to save the changes
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(save)
        layout.addWidget(self.save_button)

        self.form.show()





    
    def stop(self):
        self.running = False
    
    def run(self):
        while self.running:
            self.lc.handle()
            # self.w.setData(self.spy.data())

def main():
    udpm = getCmdOption(sys.argv, "-u=", "udpm://239.255.76.67:7667?ttl=1")
    app = QApplication([])
    Window(udpm)
    app.exec()


if __name__ == '__main__':
    main()
