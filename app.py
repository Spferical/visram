from numpy import arange, sin, pi
import matplotlib
import matplotlib.pyplot as plt

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wx import NavigationToolbar2Wx

import wx

import chart


class CanvasPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        # create the chart of processes and display it
        self.figure, self.axes = chart.create_graph()
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.SHAPED)
        self.SetSizer(self.sizer)
        self.text = None
        self.selected_wedge = None
        self.Fit()

        # When the user moves the mouse, display the name of the process
        # the selected wedge represents.
        def onmove(event):
            if event.xdata and event.ydata:

                # go through each wedge in the graph, checking to see if it
                # contains the mouse event
                for c in self.axes.get_children():
                    if isinstance(c, chart.ProcessWedge):
                        if c.contains(event):

                            # if so, and it is not the previously-selected
                            # wedge, erase the old process name text and
                            # draw it for the currently-selected process
                            if self.selected_wedge != c:
                                self.selected_wedge = c
                                (x, y) = c.get_shape_center()
                                if self.text:
                                    self.text.remove()
                                self.text = plt.text(x, y, c.process_name,
                                        figure=self.figure)
                                self.canvas.draw()
                                break
        self.canvas.mpl_connect('motion_notify_event', onmove)

if __name__ == "__main__":
    app = wx.App()
    fr = wx.Frame(None, title='test')
    panel = CanvasPanel(fr)
    fr.Show()
    app.MainLoop()
