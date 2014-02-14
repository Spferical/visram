#!/usr/bin/python2
import psutil
import matplotlib
from matplotlib.patches import Wedge
import math
from matplotlib import colors
import matplotlib.cm as cmx
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
        return self.theta2 - self.theta1

    def get_shape_center(self):
        theta = math.radians((self.theta1 + self.theta2) / 2)
        x = self.center[0] + (self.r - self.width/2)*math.cos(theta)
        y = self.center[1] + (self.r - self.width/2)*math.sin(theta)
        return (x, y)

    def get_wedge_points(self):
        points = []
        theta1 = math.radians(self.theta1)
        theta2 = math.radians(self.theta2)

        for angle in (0, math.pi / 2, math.pi, 3 * math.pi / 2,
                      theta1, theta2):
            if theta1 <= angle <= theta2:
                x = self.center[0] + (self.r) * math.cos(angle)
                y = self.center[1] + (self.r) * math.sin(angle)
                points.append((x, y))

        return points

    def get_bounds(self):
        left = right = self.center[0]
        top = bottom = self.center[1]

        for p in self.get_wedge_points():

            left = min(left, p[0])
            right = max(right, p[0])
            top = max(top, p[1])
            bottom = min(bottom, p[1])

        return (top, left, bottom, right)

    def contains(self, event):
        (x, y) = (event.xdata - self.center[0], event.ydata - self.center[1])
        angle = math.degrees(math.atan2(y, x))
        if angle < 0:
            angle += 360

        mag = math.sqrt(x ** 2 + y ** 2)
        return self.contains_polar(mag, angle)

    def contains_polar(self, r, angle_degrees):
        """
        Uses precalculated polar coordinates to determine whether the wedge
        contains a point.
        """
        angle = angle_degrees
        while angle < 0:
            angle += 360

        if self.theta1 <= angle <= self.theta2:
            if self.r - self.width <= r <= self.r:
                return True
        return False


def get_percent_including_children(p, pmap, ptree, key):
    """Gets the percent of RAM/CPU a process is using, including that used by
    all of its children."""
    try:
        processes_to_check_stack = []
        processes_to_check_stack.append(p)
        total_percent = 0
        while processes_to_check_stack:
            p = processes_to_check_stack.pop()
            try:
                total_percent += key(pmap[p.pid])
                for child in ptree[p.pid]:
                    processes_to_check_stack.append(child)
            except KeyError:
                # processes are pretty unstable
                # and may not have been put in ptree or pmap
                pass
        return total_percent
    except psutil.NoSuchProcess:
        return 0


def get_root_processes(procs):
    """Gets all processes in the system that have no parents."""
    rootprocs = []
    for proc in procs:
        if not proc.parent:
            rootprocs.append(proc)
    return rootprocs


def create_process_map():
    """Creates a dict of the dicts of each process on the system.
    Probably faster than calling p.get_whatever() many times, and, rather
    importantly, gives a /snapshot/ of the system's processes at a certain
    time.
    """
    map = {}
    for p in psutil.process_iter():
        map[p.pid] = p.as_dict(
            attrs=['pid', 'name', 'get_memory_percent', 'get_cpu_percent'])
    return map


def create_process_tree():
    """Creates a dict of the children of each process in the system.
    This is way way way faster than calling psutil.get_children()
    each time we want to iterate on a process's children.
    Indexed by process PID."""
    tree = {}
    for p in psutil.process_iter():
        tree[p.pid] = []
    for p in psutil.process_iter():
        parent = p.parent
        if parent:
            tree[parent.pid].append(p)
    return tree


def draw_proc(p, ax, start_angle, depth, pmap, ptree, center, key,
              scalar_cmap):
    """Returns the arc and bounds of the drawn wedges.
    Bounds are in the form of (top, left, bottom, right)"""
    try:
        r = 0.1 * (depth + 1)
        p_arc = get_percent_including_children(p, pmap, ptree, key) / 100 * 360
        w_color = get_color(start_angle + p_arc / 2, depth, scalar_cmap)
        try:
            name = p.name
        except psutil.AccessDenied:
            name = "ACCESS DENIED"
        wedge = ProcessWedge(
            pmap[p.pid], depth, center, r, start_angle,
            start_angle + p_arc, width=0.1, facecolor=w_color,
            linewidth=0.5, edgecolor=(0, 0, 0))
        ax.add_artist(wedge)

        bounds = wedge.get_bounds()

        # loop through each of the process's children and
        # draw them in order of memory/cpu usage (including children)
        # (this lets the user focus on the big processes more easily)
        try:
            for c in sorted(
                    ptree[p.pid],
                    key=lambda c: get_percent_including_children(c, pmap,
                        ptree, key),
                    reverse=True):
                c_wedge, c_bounds = draw_proc(
                    c, ax, start_angle, depth + 1,
                    pmap, ptree, center, key, scalar_cmap)

                # if we successfully drew the child wedge and it returned a
                # wedge, we can update the window's bounds and the start angle
                # based on it
                if c_wedge:
                    bounds = update_bounds(bounds, c_bounds)
                    start_angle += c_wedge.arc

        except KeyError:
            # processes are pretty unstable
            # and may not have been put in ptree or pmap
            pass

        return wedge, bounds
    except psutil.NoSuchProcess:
        return None, None


def get_color(theta, depth, scalar_cmap):
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


def create_graph(type, theme):
    """
    The important function: creates a graph of all processes in the system.
    Types:
        'ram' -- creates a chart of RAM usage
        'cpu' -- creates a chart of CPU usage

    theme -- the matplotlib color map to use
    """

    # create a color map mappable between 0 and 1 for the theme
    cm = cmx.get_cmap(theme)
    c_norm = colors.Normalize(vmin=0, vmax=1)
    scalar_map = cmx.ScalarMappable(norm=c_norm, cmap=cm)

    procs = psutil.process_iter()
    fig = matplotlib.figure.Figure()
    ax = fig.add_axes([0, 0, 1, .9])

    ax.tick_params(
        which='both',
        bottom='off',
        left='off',
        top='off',
        right='off',
        labelleft='off',
        labelbottom='off')

    for a in ("left", "right", "top", "bottom"):
        ax.spines[a].set_visible(False)

    if type == 'cpu':
        ax.set_title("CPU Usage")
    elif type == 'ram':
        ax.set_title("RAM Usage")
    ax.axis('scaled')
    center = (0.5, 0.5)

    root_procs = get_root_processes(procs)

    angle_so_far = 0
    bounds = (0.5, 0.5, 0.5, 0.5)

    # by default, psutil waits 0.1 seconds per get_cpu_percent() call
    # this is very slow
    # what we can do is call get_cpu_percent for each process at once,
    # then wait a bit to measure each process's CPU usage.
    # after this, p.get_cpu_percent() will return useful values
    # (even though we aren't calling this directly, it is called in
    # Process.as_dict(), so this helps)
    for p in psutil.process_iter():
        p.get_cpu_percent(interval=0)
    time.sleep(0.2)

    if type == 'cpu':

        # CPU usage total is 100% * NUM_CPUS
        # so divide by NUM_CPUs to get total percent
        key = lambda p_dict: p_dict['cpu_percent'] / psutil.NUM_CPUS

    elif type == 'ram':
        key = lambda p_dict: p_dict['memory_percent']

    pmap = create_process_map()
    ptree = create_process_tree()

    for i, p in enumerate(root_procs):
        ws, bounds2 = draw_proc(
            p, ax, angle_so_far, 0, pmap, ptree, center, key, scalar_map)
        bounds = update_bounds(bounds, bounds2)
        angle_so_far += ws.arc

    ax.set_xlim(bounds[1], bounds[3])
    ax.set_ylim(bounds[2], bounds[0])

    return fig, ax, type


def recolor(fig, ax, theme):
    """Recolors a chart for a color theme."""

    # create a color map for the theme mappable between 0 and 1
    cm = cmx.get_cmap(theme)
    c_norm = colors.Normalize(vmin=0, vmax=1)
    scalar_map = cmx.ScalarMappable(norm=c_norm, cmap=cm)

    # go through each wedge and recolor it
    for c in ax.get_children():
        if isinstance(c, ProcessWedge):
            w_color = get_color((c.theta1 + c.theta2) / 2, c.depth, scalar_map)
            c.set_facecolor(w_color)
