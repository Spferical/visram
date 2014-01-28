#!/usr/bin/python2
import matplotlib.pyplot as plt

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wx import NavigationToolbar2Wx

import wx
from wx.lib import delayedresult

import chart


class CanvasPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        self.SetAutoLayout(True)

        # create the wx panel's sizer
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        #start drawing the ram
        delayedresult.startWorker(self.draw_chart, chart.create_graph)

    def on_move(self, event):
        """To be called when the user moves the mouse.
        Displays the name of the process the hovered-over wedge represents."""
        # check if event falls within the graph
        if event.xdata and event.ydata:

            # go through each wedge in the graph, checking to see if it
            # contains the mouse event
            for c in self.axes.get_children():
                if isinstance(c, chart.ProcessWedge) and c.contains(event):

                    # if so, and it is not the previously-selected
                    # wedge, erase the old process name text and
                    # draw it for the currently-selected process
                    if self.selected_wedge != c:

                        self.selected_wedge = c
                        (x, y) = c.get_shape_center()
                        self.canvas.restore_region(self.background)

                        # remove the previous text, if any, and add some new
                        # text to the chart
                        if self.text:
                            self.text.remove()
                        self.text = plt.text(
                            x, y, c.process_name,
                            bbox=dict(boxstyle="round,pad=.5", fc="0.8"),
                            figure=self.figure)

                        # draw the text and blit it to the display
                        self.axes.draw_artist(self.text)
                        self.canvas.blit(self.axes.bbox)

                        # if we found the hovered-over wedge, we're done!
                        break

    def on_size(self, event):
        """Removes any text and resizes the canvas when the window is
        resized."""

        # remove any text that exists so that it won't be drawn on the
        # new background
        if self.text:
            self.text.remove()
            self.text = None

        # draw the canvas
        self.canvas.draw()

        # copy this plain canvas with no text to a background object
        self.background = self.canvas.copy_from_bbox(self.axes.bbox)

        # refresh the wx display
        self.Refresh()

    def draw_chart(self, delayed_result):
        # get the figure and axes
        (self.figure, self.axes) = delayed_result.get()

        #create the canvas
        self.canvas = FigureCanvas(self, -1, self.figure)

        # add the canvas to our sizer
        # the canvas is shaped, because it looks weird when stretch
        # (wedges lose proportionality and can't easily be compared)
        self.sizer.Add(self.canvas, 1,
                       wx.ALIGN_CENTER_HORIZONTAL |
                       wx.ALIGN_CENTER_VERTICAL | wx.SHAPED)

        # lay out the thing so the canvas will be drawn in the right area
        self.Layout()

        # initialize variables for manipulating the canvas
        self.text = None
        self.selected_wedge = None

        # initially draw the canvas and copy it to a background object
        self.on_size(None)

        # connect the functions to be called upon certain events
        self.canvas.mpl_connect('motion_notify_event', self.on_move)
        self.canvas.mpl_connect('resize_event', self.on_size)


class VisramFrame(wx.Frame):

    def __init__(self, *args, **kwargs):
        wx.Frame.__init__(self, *args, **kwargs)

        menu_bar = wx.MenuBar()
        menu = wx.Menu()
        exit = menu.Append(wx.ID_EXIT, "Exit",
                           "Close window and exit program.")
        menu_bar.Append(menu, "&File")
        self.Bind(wx.EVT_MENU, self.on_close, exit)
        self.SetMenuBar(menu_bar)

        self.canvas_panel = CanvasPanel(self)

        self.canvas_panel.Layout()

    def on_close(self, e):
        self.Close()


if __name__ == "__main__":
    app = wx.App()
    fr = VisramFrame(None, title='Visram')
    fr.Show()
    app.MainLoop()
