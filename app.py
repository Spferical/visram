#!/usr/bin/python2
import matplotlib

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas

import wx
from wx.lib import delayedresult

import mpltextwrap

import math

import chart


def get_matplotlib_color(wx_color):
    # matplotlib can read strings in this syntax
    return wx.Colour.GetAsString(wx_color, wx.C2S_HTML_SYNTAX)


class CanvasPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        self.SetAutoLayout(True)

        # create the wx panel's sizer
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        self.canvas = None

        # sizer to put buttons
        self.button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.button_sizer)

        # create buttons to draw the chart
        self.mem_usage_button = wx.Button(self, 1, "Draw RAM Usage")
        self.mem_usage_button.Bind(wx.EVT_BUTTON, self.on_button,
                                   self.mem_usage_button)
        self.button_sizer.Add(self.mem_usage_button, 1, wx.ALIGN_RIGHT)

        self.cpu_usage_button = wx.Button(self, 1, "Draw CPU Usage")
        self.cpu_usage_button.Bind(wx.EVT_BUTTON, self.on_button,
                                   self.mem_usage_button)
        self.button_sizer.Add(self.cpu_usage_button, 1, wx.ALIGN_RIGHT)

    def on_button(self, e):

        if self.canvas:
            self.sizer.Remove(self.canvas)
            self.canvas.Destroy()

        draw_cpu_usage = (e.GetEventObject() == self.cpu_usage_button)
        self.start_drawing_chart_in_background(draw_cpu_usage)

    def start_drawing_chart_in_background(self, cpu_usage=False):
        delayedresult.startWorker(self.draw_chart, chart.create_graph,
                                  wargs=(cpu_usage,))

        #while we're drawing the chart, disable the buttons for it
        for b in (self.cpu_usage_button, self.mem_usage_button):
            b.Disable()

    def on_move(self, event):
        """To be called when the user moves the mouse.
        Displays the name of the process the hovered-over wedge represents."""
        # check if event falls within the graph
        if event.xdata and event.ydata:

            # go through each wedge in the graph, checking to see if it
            # contains the mouse event
            xd, yd = event.xdata - 0.5, event.ydata - 0.5
            angle = math.degrees(math.atan2(yd, xd))
            r = math.sqrt(xd ** 2 + yd ** 2)
            for c in self.axes.get_children():
                if isinstance(c, chart.ProcessWedge) and \
                        c.contains_polar(r, angle):

                    # update the display
                    self.update_selected_wedge(c)

                    # if we found the hovered-over wedge, we're done!
                    break

    def update_selected_wedge(self, new_wedge):

        # erase the old process name text and
        # draw it for the currently-selected process
        if self.selected_wedge != new_wedge:

            self.selected_wedge = new_wedge
            (x, y) = new_wedge.get_shape_center()
            self.canvas.restore_region(self.background)

            # figure out how to justify the text
            # (if we just center it, weird behavior occurs near the very edges
            # and text can get cut off)
            # If the text is far to the left or right, it should be justified
            # to that side. Same for top and bottom.
            (left, right) = self.axes.get_xlim()
            (bottom, top) = self.axes.get_ylim()
            width = right - left
            height = top - bottom

            # simple solution: see which third the position is in vertically
            # and horizontally, and justify it based on that.
            # e.g. text in the left-most 1/3 is left-justified

            # horizontal justifying
            if (x < left + width / 3):
                ha = 'left'
            elif x > right - width / 3:
                ha = 'right'
            else:
                ha = 'center'

            # vertical justifying
            if y < bottom + height / 3:
                va = 'bottom'
            elif y > top - height / 3:
                va = 'top'
            else:
                va = 'center'

            # remove the previous text, if any, and add some new
            # text to the chart
            if self.text:
                self.text.remove()

            bg = get_matplotlib_color(wx.SystemSettings.GetColour(
                wx.SYS_COLOUR_INFOBK))
            textcolor = get_matplotlib_color(wx.SystemSettings.GetColour(
                wx.SYS_COLOUR_INFOTEXT))
            self.text = matplotlib.axes.Axes.text(
                self.axes,
                x, y, new_wedge.process_name,
                color=textcolor,
                bbox=dict(boxstyle="round", fc=bg, ec="none"),
                figure=self.figure,
                ha=ha,
                va=va
                )

            # autowrap the text
            mpltextwrap.autowrap_text(self.text, self.canvas.renderer)

            # draw the text and blit it to the display
            self.axes.draw_artist(self.text)
            self.canvas.blit(self.axes.bbox)


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

    def theme_chart(self):
        """
        Uses wx.SystemSettings to set the color of the chart figure's
        background and title to make it feel native.
        """
        # Set the title's color to the system's theme.
        self.axes.title.set_color(
            get_matplotlib_color(
                wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)))

        # set the background color of the figure to the system theme's color
        self.figure.set_facecolor(
            get_matplotlib_color(
                wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)))

        # set the background color of the axes to the system theme's color
        self.axes.patch.set_facecolor(
            get_matplotlib_color(
                wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)))

    def draw_chart(self, delayed_result):
        # get the figure and axes
        (self.figure, self.axes) = delayed_result.get()

        # theme the chart appropriately for the system
        self.theme_chart()

        #create the canvas
        self.canvas = FigureCanvas(self, -1, self.figure)

        # add the canvas to our sizer
        # the canvas is shaped, because it looks weird when stretch
        # (wedges lose proportionality and can't easily be compared)
        self.sizer.Add(self.canvas, 1,
                       wx.ALIGN_CENTER_HORIZONTAL |
                       wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)

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

        # we finished drawing the chart, so we can now allow the user to
        # refresh it
        for b in (self.mem_usage_button, self.cpu_usage_button):
            b.Enable()


class VisramFrame(wx.Frame):

    def __init__(self, *args, **kwargs):
        wx.Frame.__init__(self, *args, **kwargs)

        # simple menu bar
        menu_bar = wx.MenuBar()
        menu = wx.Menu()
        exit = menu.Append(wx.ID_EXIT, "Exit",
                           "Close window and exit program.")
        menu_bar.Append(menu, "&File")
        self.Bind(wx.EVT_MENU, self.on_close, exit)
        self.SetMenuBar(menu_bar)

        #create the canvas panel and lay it out
        self.canvas_panel = CanvasPanel(self)
        self.canvas_panel.Layout()

    def on_close(self, e):
        self.Close()


def main():
    app = wx.App()
    fr = VisramFrame(None, title='Visram')
    fr.Show()
    app.MainLoop()

if __name__ == "__main__":
    main()
