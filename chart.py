#!/usr/bin/python2
import psutil
import matplotlib
from matplotlib.patches import Wedge
import math
from matplotlib import colors
import matplotlib.cm as cmx


# globals for setting the colors in the chart
NUM_COLORS = 8
cm = cmx.get_cmap('spectral')
c_norm = colors.Normalize(vmin=0, vmax=NUM_COLORS - 1)
scalar_map = cmx.ScalarMappable(norm=c_norm, cmap=cm)


class ProcessWedge(Wedge):
    """ A wedge that represents a process in memory.
    Contains the name of its process and various helper methods."""
    def __init__(self, process_name, *args, **kwargs):
        self.process_name = process_name
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

        if self.theta1 <= angle <= self.theta2:
            mag = math.sqrt(x ** 2 + y ** 2)
            if self.r - self.width <= mag <= self.r:
                return True
        return False


def get_mem_percent_including_children(p, pmap, ptree):
    """Gets the percent of RAM a process is using, including that used by all
    of its children."""
    try:
        processes_to_check_stack = []
        processes_to_check_stack.append(p)
        memory_percent = 0
        while processes_to_check_stack:
            p = processes_to_check_stack.pop()
            try:
                memory_percent += pmap[p]
                for child in ptree[p]:
                    processes_to_check_stack.append(child)
            except KeyError:
                # processes are pretty unstable
                # and may not have been put in ptree or pmap
                pass
        return memory_percent
    except psutil.NoSuchProcess:
        return 0


def get_root_processes(procs):
    """Gets all processes in the system that have no parents."""
    rootprocs = []
    for proc in procs:
        if not proc.parent:
            rootprocs.append(proc)
    return rootprocs


def create_process_map(key=lambda p: p.get_memory_percent()):
    """Creates a dict the mempercents of each process on the system.
    Probably faster than calling p.get_memory_percent many many times. I
    haven't tested it though."""
    map = {}
    for p in psutil.process_iter():
        map[p] = key(p)
    return map


def create_process_tree():
    """Creates a dict of the children of each process in the system.
    This is way way way faster than calling psutil.get_children()
    each time we want to iterate on a process's children."""
    tree = {}
    for p in psutil.process_iter():
        tree[p] = p.get_children()
    return tree


def draw_proc(
        p, ax, start_angle, depth, colorindex, pmap, ptree,
        center=(0.5, 0.5)):
    """Returns the arc and bounds of the drawn wedges.
    Bounds are in the form of (top, left, bottom, right)"""
    try:
        r = 0.1 * (depth + 1)
        w_color = scalar_map.to_rgba(colorindex)
        p_arc = get_mem_percent_including_children(p, pmap, ptree) / 100 * 360
        wedge = ProcessWedge(
            p.name, center, r, start_angle,
            start_angle + p_arc, width=0.1, facecolor=w_color,
            linewidth=0.5, edgecolor=(0, 0, 0))
        ax.add_artist(wedge)
        c_colorindex = get_next_color_index(colorindex)

        bounds = wedge.get_bounds()

        # loop through each of the process's children and
        # draw them in order of memory usage (including children)
        # (this lets the user focus on the big processes more easily)
        try:
            for c in sorted(
                    ptree[p],
                    key=lambda c: get_mem_percent_including_children(c, pmap,
                                                                     ptree),
                    reverse=True):
                c_wedge, c_bounds = draw_proc(
                    c, ax, start_angle, depth + 1,
                    c_colorindex, pmap, ptree)

                # if we successfully drew the child wedge and it returned a
                # wedge, we can update the window's bounds and the start angle
                # based on it
                # also we can get a new color index
                if c_wedge:
                    bounds = update_bounds(bounds, c_bounds)
                    start_angle += c_wedge.arc
                    c_colorindex = get_next_color_index(c_colorindex)

                # can't have a child having the same color as their parent
                # or you can't tell them apart
                while c_colorindex == colorindex:
                    c_colorindex = get_next_color_index(c_colorindex)
        except KeyError:
            # processes are pretty unstable
            # and may not have been put in ptree or pmap
            pass

        return wedge, bounds
    except psutil.NoSuchProcess:
        return None, None


def update_bounds(bounds, bounds2):
    """Returns a set of bounds that contain both bounds given as arguments."""
    (top, left, bottom, right) = bounds
    (top2, left2, bottom2, right2) = bounds2
    left = min(left, left2)
    right = max(right, right2)
    top = max(top, top2)
    bottom = min(bottom, bottom2)
    return (top, left, bottom, right)


def get_next_color_index(colorindex):
    """Gets the next index of a color in the colors array.
    If the index points to the last color in the array, it returns an index
    to the first element."""
    colorindex += 1
    if colorindex >= NUM_COLORS:
        colorindex = 0
    return colorindex


def create_graph(cpu_usage=False):
    """The important function: creates a graph of all processes in the system.
    If cpu_usage is False, creates a chart of ram usage.
    If cpu_usage is True, creates a chart of cpu usage.
    """
    procs = psutil.process_iter()
    fig = matplotlib.figure.Figure()
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis('off')
    ax.axis('scaled')
    center = (0.5, 0.5)

    root_procs = get_root_processes(procs)

    angle_so_far = 0
    colorindex = 0
    bounds = (0.5, 0.5, 0.5, 0.5)

    if cpu_usage:
        key = lambda p: p.get_cpu_percent()
        pmap = create_process_map(key)
    else:
        pmap = create_process_map()

    ptree = create_process_tree()
    for p in root_procs:
        ws, bounds2 = draw_proc(
            p, ax, angle_so_far, 0, colorindex, pmap, ptree, center)
        bounds = update_bounds(bounds, bounds2)
        angle_so_far += ws.arc
        colorindex = get_next_color_index(colorindex)

    ax.set_xlim(bounds[1], bounds[3])
    ax.set_ylim(bounds[2], bounds[0])

    return fig, ax
