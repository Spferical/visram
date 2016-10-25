#!/usr/bin/env python3
"""GUI portion of Visram."""
from PyQt5 import QtGui, QtWidgets, QtCore
import matplotlib.cm as cmx
from matplotlib import colors
import sys
import time

import processes


class VisramMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Visram")
        self.resize(250, 250)

        menuBar = self.menuBar()

        helpMenu = menuBar.addMenu("&Help")

        aboutAction = QtWidgets.QAction("&Help", self)
        aboutAction.setStatusTip("Information about the program")

        helpMenu.addAction(aboutAction)

        self.chart = VisramChart(self)
        self.setCentralWidget(self.chart)

    def closeEvent(self, event):
        self.chart.close()


class VisramChart(QtWidgets.QGraphicsView):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        cmap = cmx.get_cmap('spectral')

        c_norm = colors.Normalize(vmin=0, vmax=1)

        self.colormap = cmx.ScalarMappable(norm=c_norm, cmap=cmap)

        self.setupScene()

        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        # start updater object on separate thread
        self.updateThread = QtCore.QThread()
        self.updater = Updater()
        self.updater.moveToThread(self.updateThread)
        self.updateThread.started.connect(self.updater.run)
        self.updater.update.connect(self.updateChart)
        self.updateThread.start()

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
        color = get_wedge_color(angle, depth, self.colormap)
        memory_percent = process_graph.get_percent_including_children(pid)
        if memory_percent is None:
            memory_percent = 0
        angle2 = angle + memory_percent / 100 * 360
        item = self.drawWedge(color, angle, angle2, depth, depth + 1)
        item.setToolTip(process_graph.get_name(pid))
        child_angle = angle
        sort_key = process_graph.get_percent_including_children
        child_pids = process_graph.get_child_pids(pid)
        for child_pid in sorted(child_pids, key=sort_key, reverse=True):
            child_angle = self.drawProcess(
                child_pid, child_angle, depth + 1, process_graph)
        return angle2

    def setupScene(self):
        self.scene = QtWidgets.QGraphicsScene(self)
        self.setScene(self.scene)
        self.drawWedge((1, 0.5, 0),
                       180, 340, 1, 2)

    def drawWedge(self, color, theta1, theta2, radius1, radius2):
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
        return self.scene.addPath(path, QtGui.QPen(QtCore.Qt.NoPen), brush)


class Updater(QtCore.QObject):
    update = QtCore.pyqtSignal(processes.ProcessGraph)
    stop = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run(self):
        while not self.stop:
            self.update.emit(processes.generate_process_graph())
            time.sleep(1)


def get_wedges(process_graph):
    pass


class Wedge(object):
    def __init__(self, angle1, angle2, radius1, radius2):
        self.angle1 = angle1
        self.angle2 = angle2
        self.radius1 = radius1
        self.radius2 = radius2


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


def main():
    app = QtWidgets.QApplication(sys.argv)

    w = VisramMainWindow()
    w.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
