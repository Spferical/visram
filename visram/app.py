#!/usr/bin/env python2
"""GUI portion of Visram."""
import matplotlib
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas

import wx
from wx.lib import delayedresult
from wx.lib.pubsub import setupkwargs
from wx.lib.pubsub import pub

import math
import locale
from functools import cmp_to_key

from visram import chart
from visram import mpltextwrap
import visram


def get_matplotlib_color(wx_color):
    """Returns a wx.Colour in a format that matplotlib can read."""
    return wx.Colour.GetAsString(wx_color, wx.C2S_HTML_SYNTAX)


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


def get_p_text(p_dict):
    """Returns a textual description of a process.
    Includes various info, including name, PID, CPU/RAM usage, etc.
    Includes name, PID, CPU percent, memory percent, memory usage, and the
    process's owner.
    """
    name = p_dict['name']
    pid = p_dict['pid']
    cpu_percent = p_dict['cpu_percent']
    memory_percent = p_dict['memory_percent']
    memory_usage = p_dict['memory_info']
    owner = p_dict['username']

    if cpu_percent != 'ACCESS DENIED':
        cpu_percent = '{:.2f}'.format(cpu_percent)
    if memory_percent != 'ACCESS DENIED':
        memory_percent = '{:.2f}'.format(p_dict['memory_percent']),
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


class ProcessPopup(wx.Frame):
    """Popup that displays info about a process."""
    def __init__(self, p_dict, *args, **kwargs):
        wx.Frame.__init__(self, *args, **kwargs)

        # put everything in a Panel so the background isn't gray on Windows
        self.panel = wx.Panel(self)

        self.text = wx.StaticText(self.panel, -1)

        self.panel.sizer = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetSizer(self.panel.sizer)
        self.panel.sizer.Add(self.text)

        self.update_text(p_dict)

    def update_text(self, p_dict):
        """Updates the text on the popup based on the process's dict."""
        self.text.SetLabel(get_p_text(p_dict))
        self.panel.sizer.Fit(self)


class CanvasPanel(wx.Panel):
    """Panel containing the canvas for the chart."""
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        self.SetAutoLayout(True)

        # create the wx panel's sizer
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        self.canvas = None
        self.popup = None

        # variables for manipulating the canvas
        self.text = None
        self.selected_wedge = None

        self.figure = None
        self.axes = None
        self.chart_type = None

        self.background = None

        # get theme from config if available
        # or default to 'spectral' theme
        cfg = wx.Config('visram')
        if cfg.Exists('theme'):
            self.chart_theme = cfg.Read('theme')
        else:
            self.chart_theme = 'spectral'

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

        # subscribe to colortheme change events
        pub.subscribe(self._on_colortheme_change, 'colortheme.change')

    def on_button(self, event):
        """Runs when a button is pressed.
        Based on the button, decides what chart to draw, and starts drawing
        it."""

        if event.GetEventObject() == self.cpu_usage_button:
            chart_type = 'cpu'
        else:
            chart_type = 'ram'

        self.start_drawing_chart(chart_type)

    def start_drawing_chart(self, chart_type='cpu'):
        """Starts drawing the chart in the background, using delayedresult.
        Disables the buttons for it, too."""
        delayedresult.startWorker(self.draw_chart, chart.create_chart,
                                  wargs=(chart_type, self.chart_theme))

        # while we're drawing the chart, disable the buttons for it
        for button in (self.cpu_usage_button, self.mem_usage_button):
            button.Disable()

    def on_move(self, event):
        """To be called when the user moves the mouse.
        Displays the name of the process the hovered-over wedge represents."""

        wedge_found = False

        # check if event falls within the graph
        if event.xdata and event.ydata:

            # go through each wedge in the graph, checking to see if it
            # contains the mouse event
            xdata, ydata = event.xdata - 0.5, event.ydata - 0.5
            angle = math.degrees(math.atan2(ydata, xdata))
            radius = math.sqrt(xdata ** 2 + ydata ** 2)
            for child in self.axes.get_children():
                if isinstance(child, chart.ProcessWedge) and \
                        child.contains_polar(radius, angle):

                    # update the display
                    self.update_selected_wedge(child)

                    wedge_found = True

                    # if we found the hovered-over wedge, we're done!
                    break

        # if we didn't find a wedge, clear the current one (if any)
        if not wedge_found and self.selected_wedge:
            self.clear_selected_wedge()

    def update_selected_wedge(self, new_wedge):
        """Erases the old process name text and draws it for the
        currently-selected process.
        """
        if self.selected_wedge != new_wedge:

            self.selected_wedge = new_wedge
            (wedge_x, wedge_y) = new_wedge.get_shape_center()
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
            if wedge_x < left + width / 3:
                horizontal_alignment = 'left'
            elif wedge_x > right - width / 3:
                horizontal_alignment = 'right'
            else:
                horizontal_alignment = 'center'

            # vertical justifying
            if wedge_y < bottom + height / 3:
                vertical_alignment = 'bottom'
            elif wedge_y > top - height / 3:
                vertical_alignment = 'top'
            else:
                vertical_alignment = 'center'

            # remove the previous text, if any, and add some new
            # text to the chart
            if self.text:
                self.text.remove()

            face_color = get_matplotlib_color(wx.SystemSettings.GetColour(
                wx.SYS_COLOUR_INFOBK))
            textcolor = get_matplotlib_color(wx.SystemSettings.GetColour(
                wx.SYS_COLOUR_INFOTEXT))

            process_name = new_wedge.process_info['name']
            self.text = matplotlib.axes.Axes.text(
                self.axes,
                wedge_x, wedge_y, process_name,
                color=textcolor,
                bbox=dict(boxstyle="round", fc=face_color, ec="none"),
                figure=self.figure,
                ha=horizontal_alignment,
                va=vertical_alignment
                )

            # autowrap the text
            mpltextwrap.autowrap_text(self.text, self.canvas.renderer)

            # draw the text and blit it to the display
            self.axes.draw_artist(self.text)
            self.canvas.blit(self.axes.bbox)

    def clear_selected_wedge(self):
        """Sets the selected wedge to None, restores the background of the
        canvas (erasing anything else), removes the text, if any, and blits the
        result to the canvas.
        """
        self.selected_wedge = None

        # restore the empty chart
        self.canvas.restore_region(self.background)

        if self.text:
            self.text.remove()
            self.text = None

        self.canvas.blit(self.axes.bbox)

    def on_size(self, event):
        """Removes any text and resizes the canvas when the window is
        resized.
        """

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
        """Gets the chart from the delayed result, themes it, and replaces the
        old canvas with a new one for the new chart. Enables the buttons for
        drawing subsequent charts.
        """
        # get the figure and axes
        (self.figure, self.axes, self.chart_type) = delayed_result.get()

        # theme the chart appropriately for the system
        self.theme_chart()

        # destroy the old canvas
        if self.canvas:
            self.sizer.Remove(self.canvas)
            self.canvas.Destroy()

        # create the canvas
        self.canvas = FigureCanvas(self, -1, self.figure)

        # add the canvas to our sizer
        # the canvas is shaped, because it looks weird when stretch
        # (wedges lose proportionality and can't easily be compared)
        self.sizer.Add(self.canvas, 1,
                       wx.ALIGN_CENTER_HORIZONTAL |
                       wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)

        # lay out the thing so the canvas will be drawn in the right area
        self.Layout()

        # initially draw the canvas and copy it to a background object
        self.on_size(None)

        # connect the functions to be called upon certain events
        self.canvas.mpl_connect('motion_notify_event', self.on_move)
        self.canvas.mpl_connect('resize_event', self.on_size)
        self.canvas.mpl_connect('button_press_event', self.on_mouse_click)

        # we finished drawing the chart, so we can now allow the user to
        # refresh it
        for button in (self.mem_usage_button, self.cpu_usage_button):
            button.Enable()

    def on_mouse_click(self, event):
        """Runs on mouse click.
        If a wedge is selected, opens a ProcessPopup for the wedge's
        process.
        """
        if self.selected_wedge:
            p_dict = self.selected_wedge.process_info
            if self.popup:
                self.popup.update_text(p_dict)
            else:
                self.popup = ProcessPopup(
                    p_dict, self,
                    style=wx.SYSTEM_MENU | wx.CLOSE_BOX |
                    wx.CAPTION | wx.FRAME_FLOAT_ON_PARENT)
            self.popup.Show()

    def _on_colortheme_change(self, chart_theme):
        """Sets the colortheme value and recolors the chart, if any.
        Removes and deletes hover text, if any."""
        self.chart_theme = chart_theme

        if self.canvas:
            # remove the text from the figure (if any)
            # otherwise, it can get in the background image
            if self.text:
                self.text.remove()
                self.text = None

            chart.recolor(self.axes, chart_theme)
            self.canvas.draw()
            self.background = self.canvas.copy_from_bbox(self.axes.bbox)


class VisramFrame(wx.Frame):
    """Frame that contains the menu bar, preferences window, and the canvas
    panel.
    """
    def __init__(self, *args, **kwargs):
        wx.Frame.__init__(self, *args, **kwargs)

        # simple menu bar
        menu_bar = wx.MenuBar()

        file_menu = wx.Menu()
        exit = file_menu.Append(wx.ID_EXIT, "Exit",
                                "Close window and exit program.")
        menu_bar.Append(file_menu, "&File")

        edit_menu = wx.Menu()
        preferences = edit_menu.Append(wx.ID_PREFERENCES, "Preferences",
                                       "Edit the colors, etc.")
        menu_bar.Append(edit_menu, "&Edit")

        help_menu = wx.Menu()
        about = help_menu.Append(wx.ID_ABOUT, "About",
                                 "Information about the program")
        menu_bar.Append(help_menu, "&Help")

        self.Bind(wx.EVT_MENU, self.on_close, exit)
        self.Bind(wx.EVT_MENU, self.on_preferences, preferences)
        self.Bind(wx.EVT_MENU, self.on_about, about)

        self.prefs = None
        self.about = None

        self.SetMenuBar(menu_bar)

        # create the canvas panel and lay it out
        self.canvas_panel = CanvasPanel(self)
        self.canvas_panel.Layout()

    def on_close(self, event):
        """Closes the window."""
        self.Close()

    def on_preferences(self, event):
        """Shows a preferences window if not already shown."""
        if not self.prefs:
            self.prefs = PreferencesFrame(
                self, style=wx.SYSTEM_MENU | wx.CLOSE_BOX | wx.CAPTION |
                wx.FRAME_FLOAT_ON_PARENT)
        self.prefs.Show()

    def on_about(self, event):
        """Shows an about dialog if not already shown."""
        # create the about dialog and populate it with information
        about_info = wx.AboutDialogInfo()
        about_info.SetName("Visram")
        about_info.SetDescription(visram.__description__)
        about_info.SetVersion(visram.__version__)
        about_info.SetDevelopers([visram.__author__])
        about_info.SetCopyright(visram.__copyright__)
        wx.AboutBox(about_info)



class PreferencesFrame(wx.Frame):
    """Frame for management of a user's preferences.
    For now, contains a combobox for color theme selection and a button for
    saving.
    """
    def __init__(self, *args, **kwargs):

        # get the current config settings
        self.cfg = wx.Config('visram')
        if self.cfg.Exists('theme'):
            theme = self.cfg.Read('theme')
        else:
            # default theme
            theme = 'spectral'

        kwargs['title'] = "Visram Preferences"
        wx.Frame.__init__(self, *args, **kwargs)

        # put everything in a Panel so the background isn't gray on Windows
        self.panel = wx.Panel(self)

        # text and combobox for setting theme
        self.theme_label = wx.StaticText(self.panel, -1, "Color Scheme")
        self.theme_combobox = wx.ComboBox(
            self.panel, -1, style=wx.CB_READONLY, value=theme,
            # sort the choices based on the current locale
            choices=sorted(matplotlib.cm.cmap_d.keys(),
                           key=cmp_to_key(locale.strcoll)))

        # button for saving preferences
        self.save_button = wx.Button(self.panel, 1, "Save settings")
        self.save_button.Bind(wx.EVT_BUTTON, self.on_save,
                              self.save_button)

        # sizer stuff
        self.panel.sizer = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetSizer(self.panel.sizer)
        self.panel.sizer.Add(self.theme_label)
        self.panel.sizer.Add(self.theme_combobox, 1)
        self.panel.sizer.Add(self.save_button, 1)
        self.panel.sizer.Fit(self)

        self.Bind(wx.EVT_COMBOBOX, self.on_colortheme_pick,
                  self.theme_combobox)

        self.message_dialog = None

    def on_colortheme_pick(self, event):
        """Sends a message when colortheme changes."""
        pub.sendMessage('colortheme.change',
                        chart_theme=self.theme_combobox.GetValue())

    def on_save(self, event):
        """Saves the current settings."""
        theme = self.theme_combobox.GetValue()

        # display a messsage about whether the save was successful
        if self.cfg.Write('theme', theme):
            message = "Save successful!"
        else:
            message = "Uh-oh! Save unsuccessful!"
        self.message_dialog = wx.MessageDialog(
            self, message, style=wx.OK | wx.CENTRE)
        self.message_dialog.ShowModal()


def main():
    """Runs the application"""
    app = wx.App()
    frame = VisramFrame(None, title='Visram', size=wx.Size(460, 480))
    frame.Show()
    app.MainLoop()

if __name__ == "__main__":
    main()
