#
# ------------------------------------------------------------
# Copyright (c) All rights reserved 
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#


import sys
import zmq
import numpy as np
from basil import dut
from PyQt4 import Qt
from PyQt4.QtCore import pyqtSlot
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
from pyqtgraph.dockarea import DockArea, Dock
import pyqtgraph.ptime as ptime
from threading import Event
from pybar.analysis.RawDataConverter.data_interpreter import PyDataInterpreter
from pybar.analysis.RawDataConverter.data_histograming import PyDataHistograming



class DataWorker(QtCore.QObject):
    run_start = QtCore.pyqtSignal()
    config_data = QtCore.pyqtSignal(dict)
    interpreted_data = QtCore.pyqtSignal(dict)
    meta_data = QtCore.pyqtSignal(dict)
    finished = QtCore.pyqtSignal()

    def __init__(self):
        QtCore.QObject.__init__(self)
        self.integrate_readouts = 1
        self._stop_readout = Event()
        self.n_bins = 512
        self.hist_range = (0, 2**14)
        self.histogram = np.zeros(self.n_bins)
        
    def connect(self, socket_addr):
        self.socket_addr = socket_addr
        self.context = zmq.Context()
        self.socket_pull = self.context.socket(zmq.PULL)
        self.socket_pull.connect(self.socket_addr)
        self.poller = zmq.Poller()  # poll needed to be able to return QThread
        self.poller.register(self.socket_pull, zmq.POLLIN)

    def on_set_integrate_readouts(self, value):
        self.integrate_readouts = value

    def process_data(self):  # infinite loop via QObject.moveToThread(), does not block event loop
        while(not self._stop_readout.wait(0.001)):  # use wait(), do not block here
            try:
                meta_data = self.socket_pull.recv_json(flags=zmq.NOBLOCK)
                data = self.socket_pull.recv()
                
                # reconstruct numpy array
                buf = buffer(data)
                dtype = meta_data.pop('dtype')
                shape = meta_data.pop('shape')
                threshold = meta_data.pop('thr')
                data_array = np.frombuffer(buf, dtype=dtype).reshape(shape)
                
                hist, bin_edges = np.histogram(np.amax(data_array, axis=1), bins=self.n_bins, range=self.hist_range)
                
                self.histogram += hist
                #for event_data in data_array:
                self.interpreted_data.emit({
                                            "waveform": data_array[0],
                                            "bin_edges": bin_edges,
                                            "histogram": self.histogram,
                                            "threshold": threshold,
                                            "n_actual_events": data_array.shape[0]
                                            })
            except zmq.Again:
                pass

        self.finished.emit()

    def stop(self):
        self._stop_readout.set()


class OnlineMonitorApplication(QtGui.QMainWindow):

    def __init__(self, socket_addr):
        super(OnlineMonitorApplication, self).__init__()
        self.setup_plots()
        self.add_widgets()
        self.fps = 0
        self.eps = 0  # events per second
        self.total_events = 0
        self.total_readouts = 0
        self.last_total_events = 0
        self.updateTime = ptime.time()
        self.total_events = 0
        self.setup_data_worker_and_start(socket_addr)

    def closeEvent(self, event):
        super(OnlineMonitorApplication, self).closeEvent(event)
        # wait for thread
        self.worker.stop()
        self.thread.wait(1) # fixes message: QThread: Destroyed while thread is still running

    def setup_data_worker_and_start(self, socket_addr):
        self.thread = QtCore.QThread()  # no parent
        self.worker = DataWorker()  # no parent
        self.worker.interpreted_data.connect(self.on_interpreted_data)
        self.worker.run_start.connect(self.on_run_start)
        self.worker.config_data.connect(self.on_config_data)
        self.spin_box.valueChanged.connect(self.worker.on_set_integrate_readouts)
        self.worker.moveToThread(self.thread)
        self.worker.connect(socket_addr)
        self.thread.started.connect(self.worker.process_data)
        self.worker.finished.connect(self.thread.quit)
        self.thread.start()

    def setup_plots(self):
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

    def add_widgets(self):
        # Main window with dock area
        self.dock_area = DockArea()
        self.setCentralWidget(self.dock_area)

        # Docks
        dock_waveform = Dock("Waveform", size=(600, 400))
        dock_histogram = Dock("Histogram", size=(600, 400))
        dock_status = Dock("Status", size=(1200, 40))
        self.dock_area.addDock(dock_waveform, 'left')
        self.dock_area.addDock(dock_histogram, 'right', dock_waveform)
        self.dock_area.addDock(dock_status, 'top')

        # Status widget
        cw = QtGui.QWidget()
        cw.setStyleSheet("QWidget {background-color:white}")
        layout = QtGui.QGridLayout()
        cw.setLayout(layout)
        self.event_rate_label = QtGui.QLabel("Event Rate\n0 Hz")
        self.spin_box = Qt.QSpinBox(value=20, maximum=1000)
        layout.addWidget(self.event_rate_label, 0, 4, 0, 1)
        layout.addWidget(self.spin_box, 0, 6, 0, 1)
        dock_status.addWidget(cw)

        # Different plot docks
        waveform_widget = pg.PlotWidget(background="w")
        self.waveform_plot = waveform_widget.plot(range(0, 200), np.zeros(shape=(200)))
        dock_waveform.addWidget(waveform_widget)

        histogram_widget = pg.PlotWidget(background="w")
        self.histogram_plot = histogram_widget.plot(range(0, 2**14 + 1), np.zeros(shape=(2**14)), stepMode=True)
        histogram_widget.showGrid(y=True)
        dock_histogram.addWidget(histogram_widget)
        
        self.thr_line = pg.InfiniteLine(pos=1000, angle=0, pen={'color':0.0, 'style':QtCore.Qt.DashLine})
        waveform_widget.addItem(self.thr_line)
        
        self.thr_line_hist = pg.InfiniteLine(pos=1000, angle=90, pen={'color':0.0, 'style':QtCore.Qt.DashLine})
        histogram_widget.addItem(self.thr_line_hist)

    @pyqtSlot()
    def on_run_start(self):
        pass

    @pyqtSlot(dict)
    def on_config_data(self, config_data):
        pass

    def setup_config_text(self, conf):
        pass

    @pyqtSlot(dict)
    def on_interpreted_data(self, interpreted_data):
        self.update_plots(**interpreted_data)

    def update_plots(self, waveform, bin_edges, histogram, threshold, n_actual_events):
        self.total_events += n_actual_events
        self.total_readouts += 1
        if self.spin_box.value() > 0 and self.total_readouts % self.spin_box.value() == 0:  # only refresh plot every spin_box.value() readout 
            self.waveform_plot.setData(x=range(0, waveform.shape[0]), y=waveform, fillLevel=0, brush=(0, 0, 255, 150))
            self.histogram_plot.setData(x=bin_edges, y=histogram, fillLevel=0, brush=(0, 0, 255, 150))
            self.thr_line.setValue(threshold)
            self.thr_line_hist.setValue(threshold)
            self.update_monitor()

    def update_monitor(self):
        now = ptime.time()
        recent_eps = (self.total_events - self.last_total_events) / (now - self.updateTime)
        self.last_total_events = self.total_events
        self.updateTime = now
        self.eps = self.eps * 0.98 + recent_eps * 0.02
        if self.spin_box.value() == 0:  # show number of events
            self.event_rate_label.setText("Total Events\n%d" % int(self.total_events))
        else:
            self.event_rate_label.setText("Event Rate\n%d Hz" % int(self.eps))


if __name__ == '__main__':
    app = Qt.QApplication(sys.argv)
#     app.aboutToQuit.connect(myExitHandler)
    win = OnlineMonitorApplication(socket_addr='tcp://127.0.0.1:5678')
    win.resize(800, 840)
    win.setWindowTitle('Online Monitor')
    win.show()
    sys.exit(app.exec_())
