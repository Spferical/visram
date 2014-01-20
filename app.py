from numpy import arange, sin, pi
import matplotlib

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wx import NavigationToolbar2Wx

import wx

import chart

class CanvasPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.figure, self.axes = chart.create_graph()
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.SHAPED)
        self.SetSizer(self.sizer)
        self.Fit()

        def onclick(event):
            print 'button=%d, x=%d, y=%d, xdata=%f, ydata=%f'%(
                event.button, event.x, event.y, event.xdata, event.ydata)
        self.canvas.mpl_connect('button_press_event', onclick)

if __name__ == "__main__":
    app = wx.App()
    fr = wx.Frame(None, title='test')
    panel = CanvasPanel(fr)
    fr.Show()
    app.MainLoop()
