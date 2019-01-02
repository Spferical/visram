#!/usr/bin/env python3
"""GUI portion of Visram."""
from PyQt5 import QtGui, QtWidgets, QtCore
import matplotlib.cm as cmx
from matplotlib import colors
import sys
import time

from visram import processes
import visram


class VisramMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Visram")
        self.resize(460, 480)

        menuBar = self.menuBar()

        helpMenu = menuBar.addMenu("&Help")

        self.about = None

        aboutAction = QtWidgets.QAction("&Help", self)
        aboutAction.setStatusTip("Information about the program")

        def showAbout():
            title = "Visram " + visram.__version__
            content = visram.__description__
            self.about = QtWidgets.QMessageBox.about(self, title, content)

        aboutAction.triggered.connect(showAbout)

        helpMenu.addAction(aboutAction)

        self.setCentralWidget(VisramMainWidget())


class VisramMainWidget(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.backgroundThread = None

        vbox = QtWidgets.QVBoxLayout()
        drawButton = QtWidgets.QPushButton("Draw RAM Usage Chart")
        drawButton.clicked.connect(self._update_graph_in_background_thread)
        self.chart = VisramChart(self)
        vbox.addWidget(drawButton)
        vbox.addWidget(self.chart)

        self.setLayout(vbox)

    def closeEvent(self, event):
        self.chart.close()

    def onResultsReady(self, process_graph):
        self.backgroundThread.quit()
        self.backgroundThread.wait()
        self.chart.updateChart(process_graph)
        self.backgroundThread = None

    def _update_graph_in_background_thread(self):
        if self.backgroundThread is None:
            # start updater object on separate thread
            self.backgroundThread = QtCore.QThread()
            self.worker = ProcessReader()
            self.worker.moveToThread(self.backgroundThread)
            self.backgroundThread.started.connect(self.worker.run)
            self.worker.resultsReady.connect(self.onResultsReady)
            self.backgroundThread.start()


class VisramChart(QtWidgets.QGraphicsView):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._process_graph = None
        self._process_popup = None

        cmap = cmx.get_cmap('nipy_spectral')

        c_norm = colors.Normalize(vmin=0, vmax=1)

        self.colormap = cmx.ScalarMappable(norm=c_norm, cmap=cmap)

        self.setRenderHints(QtGui.QPainter.Antialiasing)

        self.setupScene()

        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

    def close(self):
        """
        Stops worker thread and waits for it to finish.
        """
        self.updater.stop = True
        self.updateThread.quit()
        while self.updateThread.isRunning():
            time.sleep(0.1)

    def resizeEvent(self, event):
        self.fitInView(self.scene.sceneRect(),
                       mode=QtCore.Qt.KeepAspectRatio)

    def updateChart(self, process_graph):
        """
        Clears and redraws the chart of all the processes based on the
        the passed-in process graph.
        """
        self._process_graph = process_graph
        self.scene.clear()
        angle = 0
        sort_key = process_graph.get_percent_including_children
        root_pids = process_graph.get_root_pids()
        for pid in sorted(root_pids, key=sort_key, reverse=True):
            angle = self.drawProcess(pid, angle, 0,
                                     process_graph)
        self.fitInView(self.scene.sceneRect(),
                       mode=QtCore.Qt.KeepAspectRatio)
        self.scene.invalidate()
        self.scene.update(self.scene.sceneRect())
        self.update()

    def drawProcess(self, pid, angle, depth, process_graph):
        """
        Recursive function to draw a given process and all its children.
        """
        memory_percent = process_graph.get_percent_including_children(pid)
        if memory_percent is None:
            memory_percent = 0
        angle2 = angle + memory_percent / 100 * 360
        color = get_wedge_color((angle + angle2) / 2, depth, self.colormap)
        self.drawWedge(color, angle, angle2, depth, depth + 1, pid,
                       process_graph)
        child_angle = angle
        sort_key = process_graph.get_percent_including_children
        child_pids = process_graph.get_child_pids(pid)
        for child_pid in sorted(child_pids, key=sort_key, reverse=True):
            child_angle = self.drawProcess(
                child_pid, child_angle, depth + 1, process_graph)
        return angle2

    def setupScene(self):
        """
        Initializes the QGraphicsScene with the right background/etc.
        """
        self.scene = QtWidgets.QGraphicsScene(self)
        self.setScene(self.scene)
        self.scene.setBackgroundBrush(
            self.palette().color(QtGui.QPalette.Background))

    def drawWedge(self, color, theta1, theta2, radius1, radius2, pid,
                  process_graph):
        """
        Draws a wedge to our graphics scene with the given polar coordinates.
        """
        innerRect = QtCore.QRectF(-radius1, -radius1,
                                  radius1 * 2, radius1 * 2)
        outerRect = QtCore.QRectF(-radius2, -radius2,
                                  radius2 * 2, radius2 * 2)
        path = QtGui.QPainterPath()
        # move to starting corner
        path.arcMoveTo(innerRect, theta1)
        # arc towards opposite corner
        path.arcTo(outerRect, theta1, theta2 - theta1)
        # move back down to starting corner, closing path
        path.arcTo(innerRect, theta2, theta1 - theta2)

        brush = QtGui.QBrush(QtGui.QColor(*(c * 255 for c in color)))

        item = ProcessWedge(pid, path)
        item.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        item.setBrush(brush)

        item.setToolTip(process_graph.get_name(pid))

        self.scene.addItem(item)

    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        if item is not None:
            pid = item.pid
            text = get_p_text(pid, self._process_graph)
            if self._process_popup is None:
                self._process_popup = QtWidgets.QMessageBox(
                    QtWidgets.QMessageBox.Information,
                    self._process_graph.get_name(pid),
                    text, parent=self)
                self._process_popup.setModal(False)
            else:
                self._process_popup.setWindowTitle(
                    self._process_graph.get_name(pid))
                self._process_popup.setText(text)
            self._process_popup.show()


class ProcessWedge(QtWidgets.QGraphicsPathItem):
    def __init__(self, pid, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pid = pid


class ProcessReader(QtCore.QObject):
    """
    Class that updates a graph of all processes in a background thread and
    emits it in the new_processes signal.
    """
    resultsReady = QtCore.pyqtSignal(processes.ProcessGraph)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run(self):
        self.resultsReady.emit(processes.generate_process_graph())


def get_wedge_color(theta, depth, scalar_cmap):
    """Gets a color for a wedge to be, of the form
    (r, g, b, a).
    Each component is scaled from 0 to 1."""
    # get the index of the color in the colormap
    # (convert from degrees to float 0-to-1)
    color_index = theta / 360.0
    # get the color at that index
    color = scalar_cmap.to_rgba(color_index)

    # modify the alpha of the color
    # greater depths --> lighter color
    amod = 0.8 ** (depth)
    color = (
        color[0],
        color[1],
        color[2],
        color[3] * amod)

    return color


def get_p_text(pid, process_graph):
    """Returns a textual description of a process.
    Includes various info, including name, PID, CPU/RAM usage, etc.
    Includes name, PID, CPU percent, memory percent, memory usage, and the
    process's owner.
    """
    name = process_graph.get_name(pid)
    cpu_percent = process_graph.get_cpu_percent(pid)
    memory_percent = process_graph.get_memory_percent(pid)
    memory_usage = process_graph.get_memory_info(pid)
    owner = process_graph.get_username(pid)

    if cpu_percent != 'ACCESS DENIED':
        cpu_percent = '{:.2f}'.format(cpu_percent)
    if memory_percent != 'ACCESS DENIED':
        memory_percent = '{:.2f}'.format(memory_percent)
    if memory_usage != 'ACCESS DENIED':
        memory_usage = sizeof_fmt(memory_usage[0])

    text = '\n'.join((
        'Name: %s' % name,
        'PID: %s' % pid,
        'CPU percent: %s' % cpu_percent,
        'Memory percent: %s' % memory_percent,
        'Memory usage: %s' % memory_usage,
        'Owner: %s' % owner))
    return text


def sizeof_fmt(num):
    """
    Returns a number of bytes in a more human-readable form.
    Scaled to the nearest unit that there are less than 1024 of, up to
    a maximum of TBs.
    Thanks to stackoverflow.com/questions/1094841.
    """
    for unit in ['bytes', 'KB', 'MB', 'GB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, unit)
        num /= 1024.0
    return "%3.1f%s" % (num, 'TB')


def main():
    app = QtWidgets.QApplication(sys.argv)

    w = VisramMainWindow()
    w.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
