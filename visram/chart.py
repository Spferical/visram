#!/usr/bin/env python2
"""The chart-drawing part of Visram."""
import psutil
from matplotlib.patches import Wedge
from matplotlib import colors
import matplotlib.cm as cmx
import matplotlib.figure
import math
import time


class ProcessWedge(Wedge):
    """ A wedge that represents a process in memory.
    Contains a dict of the info about its process and various helper methods.
    """
    def __init__(self, process_info, depth, *args, **kwargs):
        self.process_info = process_info
        self.depth = depth
        Wedge.__init__(self, *args, **kwargs)

    @property
    def arc(self):
        """Returns the arc, in degrees, of this wedge."""
        return self.theta2 - self.theta1

    def get_shape_center(self):
        """Returns the center of the shape."""
        theta = math.radians((self.theta1 + self.theta2) / 2)
        center_x = self.center[0] + (self.r - self.width/2)*math.cos(theta)
        center_y = self.center[1] + (self.r - self.width/2)*math.sin(theta)
        return (center_x, center_y)

    def get_wedge_points(self):
        """Returns a list of points of the edges of the wedge.
        Includes points at the start and end angle as well as at the
        quadrilaterals.
        Used for determining the bounds of the chart."""
        points = []
        theta1 = math.radians(self.theta1)
        theta2 = math.radians(self.theta2)

        for angle in (0, math.pi / 2, math.pi, 3 * math.pi / 2,
                      theta1, theta2):
            if theta1 <= angle <= theta2:
                point_x = self.center[0] + (self.r) * math.cos(angle)
                point_y = self.center[1] + (self.r) * math.sin(angle)
                points.append((point_x, point_y))

        return points

    def get_bounds(self):
        """Returns a (top, left, bottom, right) tuple for the rectangle that
        contains all of the points in get_wedge_points()"""
        left = right = self.center[0]
        top = bottom = self.center[1]

        for point in self.get_wedge_points():

            left = min(left, point[0])
            right = max(right, point[0])
            top = max(top, point[1])
            bottom = min(bottom, point[1])

        return (top, left, bottom, right)

    def contains_event(self, event):
        """Returns whether the wedge contains a given event with xdata and
        ydata.
        """
        return self.contains_point(event.xdata, event.ydata)

    def contains_point(self, x, y):
        relative_x = x - self.center[0]
        relative_y = y - self.center[1]
        angle = math.degrees(math.atan2(relative_y, relative_x))
        if angle < 0:
            angle += 360

        mag = math.sqrt(relative_x ** 2 + relative_y ** 2)
        return self.contains_polar(mag, angle)

    def contains_polar(self, radius, angle_degrees):
        """
        Uses precalculated polar coordinates to determine whether the wedge
        contains a point.
        """
        angle = angle_degrees
        while angle < 0:
            angle += 360

        if self.theta1 <= angle <= self.theta2:
            if self.r - self.width <= radius <= self.r:
                return True
        return False


def get_percent_including_children(process, p_dicts, p_childrens, key):
    """Gets the percent of RAM/CPU a process is using, including that used by
    all of its children."""
    try:
        processes_to_check_stack = []
        processes_to_check_stack.append(process)
        total_percent = 0
        while processes_to_check_stack:
            process = processes_to_check_stack.pop()
            try:
                total_percent += key(p_dicts[process.pid])
                for child in p_childrens[process.pid]:
                    processes_to_check_stack.append(child)
            except KeyError:
                # processes are pretty unstable
                # and may not have been put in p_childrens or p_dicts
                pass
        return total_percent
    except psutil.NoSuchProcess:
        return 0


def get_root_processes(procs):
    """Gets all processes in the system that have no parents."""
    rootprocs = []
    for proc in procs:
        # processes without parents are root processes
        # WORKAROUND FOR OSX: pid 0's parent is itself, so we need to check
        # if a process's parent is itself
        if not proc.parent() or proc.parent().pid == proc.pid:
            rootprocs.append(proc)
    return rootprocs


def create_process_dict_map():
    """Creates a dict of the dicts of each process on the system.
    Probably faster than calling p.get_whatever() many times, and, rather
    importantly, gives a /snapshot/ of the system's processes at a certain
    time.
    """
    dict_map = {}
    for process in psutil.process_iter():
        dict_map[process.pid] = process.as_dict(
            attrs=['pid', 'name', 'memory_percent', 'cpu_percent',
                   'username', 'memory_info'],
            ad_value="ACCESS DENIED")
    return dict_map


def create_process_children_map():
    """Creates a dict of the children of each process in the system.
    This is way way way faster than calling psutil.get_children()
    each time we want to iterate on a process's children.
    Indexed by process PID.
    """
    child_map = {}

    # create a list for each process
    for process in psutil.process_iter():
        child_map[process.pid] = []

    # add each process to its parent's child list
    for process in psutil.process_iter():
        parent = process.parent()
        # in OSX, the process with PID=0 is it's own parent. We need to check
        # for recursive relationships like this to prevent infinite recursion.
        if parent and parent.pid != process.pid:
            child_map[parent.pid].append(process)
    return child_map


def draw_proc(process, axes, start_angle, depth, p_dicts, p_childrens, center,
              key, scalar_cmap):
    """Draws the wedge for a process.
    Returns the arc and bounds of the drawn wedges.
    Bounds are in the form of (top, left, bottom, right).
    """
    try:
        radius = 0.1 * (depth + 1)
        p_arc = get_percent_including_children(
            process, p_dicts, p_childrens, key) / 100 * 360
        w_color = get_color(start_angle + p_arc / 2, depth, scalar_cmap)
        wedge = ProcessWedge(
            p_dicts[process.pid], depth, center, radius, start_angle,
            start_angle + p_arc, width=0.1, facecolor=w_color,
            linewidth=.25)
        axes.add_artist(wedge)

        bounds = wedge.get_bounds()

        # loop through each of the process's children and
        # draw them in order of memory/cpu usage (including children)
        # (this lets the user focus on the big processes more easily)
        try:
            for child in sorted(
                    p_childrens[process.pid],
                    key=lambda child: get_percent_including_children(
                        child, p_dicts, p_childrens, key),
                    reverse=True):
                c_wedge, c_bounds = draw_proc(
                    child, axes, start_angle, depth + 1,
                    p_dicts, p_childrens, center, key, scalar_cmap)

                # if we successfully drew the child wedge and it returned a
                # wedge, we can update the window's bounds and the start angle
                # based on it
                if c_wedge:
                    bounds = update_bounds(bounds, c_bounds)
                    start_angle += c_wedge.arc

        except KeyError:
            # processes are pretty unstable
            # and may not have been put in p_childrens or p_dicts
            pass

        return wedge, bounds
    except psutil.NoSuchProcess:
        return None, None


def get_color(theta, depth, scalar_cmap):
    """Gets a color for a wedge to be."""
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


def update_bounds(bounds, bounds2):
    """Returns a set of bounds that contain both bounds given as arguments."""
    (top, left, bottom, right) = bounds
    (top2, left2, bottom2, right2) = bounds2
    left = min(left, left2)
    right = max(right, right2)
    top = max(top, top2)
    bottom = min(bottom, bottom2)
    return (top, left, bottom, right)


def create_chart(chart_type, theme):
    """
    The important function: creates a graph of all processes in the system.
    Types:
        'ram' -- creates a chart of RAM usage
        'cpu' -- creates a chart of CPU usage

    theme -- the matplotlib color map to use

    Returns a tuple of the produced figure, axes, and chart type.
    """

    # create a color map mappable between 0 and 1 for the theme
    cmap = cmx.get_cmap(theme)
    c_norm = colors.Normalize(vmin=0, vmax=1)
    scalar_map = cmx.ScalarMappable(norm=c_norm, cmap=cmap)

    procs = psutil.process_iter()
    fig = matplotlib.figure.Figure()
    axes = fig.add_axes([0, 0, 1, .9])

    axes.tick_params(
        which='both',
        bottom='off',
        left='off',
        top='off',
        right='off',
        labelleft='off',
        labelbottom='off')

    for spine in ("left", "right", "top", "bottom"):
        axes.spines[spine].set_visible(False)

    if chart_type == 'cpu':
        axes.set_title("CPU Usage")
    elif chart_type == 'ram':
        axes.set_title("RAM Usage")
    axes.axis('scaled')
    center = (0.5, 0.5)

    root_procs = get_root_processes(procs)

    angle_so_far = 0
    bounds = (0.5, 0.5, 0.5, 0.5)

    # by default, psutil waits 0.1 seconds per cpu_percent() call
    # this is very slow
    # what we can do is call cpu_percent for each process at once,
    # then wait a bit to measure each process's CPU usage.
    # after this, p.cpu_percent() will return useful values
    # (even though we aren't calling this directly, it is called in
    # Process.as_dict(), so this helps)
    for process in psutil.process_iter():
        try:
            process.cpu_percent(interval=0)
        except psutil.AccessDenied:
            pass  # just skip processes we can't read
    time.sleep(0.2)

    if chart_type == 'cpu':
        def key(p_dict):
            # first check if we can access it
            percent = p_dict['cpu_percent']
            if percent == 'ACCESS DENIED':
                return 0

            # CPU usage total is 100% * NUM_CPUS
            # so divide by NUM_CPUs to get total percent
            return percent / psutil.cpu_count()

    elif chart_type == 'ram':
        def key(p_dict):
            # return 0 if we can't access it
            percent = p_dict['memory_percent']
            if percent == 'ACCESS DENIED':
                return 0

            # else return it
            return percent

    p_dicts = create_process_dict_map()
    p_childrens = create_process_children_map()

    for process in root_procs:
        wedge, bounds2 = draw_proc(
            process, axes, angle_so_far, 0, p_dicts, p_childrens, center, key,
            scalar_map)
        bounds = update_bounds(bounds, bounds2)
        angle_so_far += wedge.arc

    axes.set_xlim(bounds[1], bounds[3])
    axes.set_ylim(bounds[2], bounds[0])

    return fig, axes, chart_type


def recolor(axes, theme):
    """Recolors a chart for a color theme."""

    # create a color map for the theme mappable between 0 and 1
    cmap = cmx.get_cmap(theme)
    c_norm = colors.Normalize(vmin=0, vmax=1)
    scalar_map = cmx.ScalarMappable(norm=c_norm, cmap=cmap)

    # go through each wedge and recolor it
    for child in axes.get_children():
        if isinstance(child, ProcessWedge):
            w_color = get_color(
                (child.theta1 + child.theta2) / 2, child.depth, scalar_map)
            child.set_facecolor(w_color)
