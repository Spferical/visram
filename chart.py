import psutil
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge
import math


# array of colors to color the wedges of the chart with
colors = "bgrcmy"


class WedgeShape(object):
    """Helper class to store the physical characteristics of a wedge in the
    graph."""
    def __init__(self, center, theta1, theta2, radius):
        self.center = center
        self.theta1 = theta1
        self.theta2 = theta2
        self.radius = radius
        self.width = 0.1

    @property
    def arc(self):
        return self.theta2 - self.theta1

    def get_shape_center(self):
        theta = math.pi*(self.theta1 + self.theta2)/180
        x = center[0] + (self.radius - self.width/2)*math.cos(theta/2)
        y = center[1] + (self.radius - self.width/2)*math.sin(theta/2)
        return (x, y)

    def get_wedge_points(self):
        angle1 = math.radians(self.theta1)
        angle2 = math.radians(self.theta2)
        x1 = self.center[0] + (self.radius)*math.cos(angle1)
        y1 = self.center[1] + (self.radius)*math.sin(angle1)
        x2 = self.center[0] + (self.radius)*math.cos(angle2)
        y2 = self.center[1] + (self.radius)*math.sin(angle2)
        return ((x1, y1), (x2, y2))

    def get_bounds(self):
        angle1 = math.radians(self.theta1)
        angle2 = math.radians(self.theta2)
        x1 = self.center[0] + (self.radius)*math.cos(angle1)
        y1 = self.center[1] + (self.radius)*math.sin(angle1)
        x2 = self.center[0] + (self.radius)*math.cos(angle2)
        y2 = self.center[1] + (self.radius)*math.sin(angle2)

        left = min(self.center[0], x1, x2)
        right = max(self.center[0], x1, x2)
        top = max(self.center[1], y1, y2)
        bottom = min(self.center[1], y1, y2)

        return (top, left, bottom, right)


def get_mem_percent_including_children(p):
    """Gets the percent of RAM a process is using, including that used by all
    of its children."""
    try:
        processes_to_check_stack = []
        processes_to_check_stack.append(p)
        memory_percent = 0
        while processes_to_check_stack:
            p = processes_to_check_stack.pop()
            memory_percent += p.get_memory_percent()
            for child in p.get_children():
                processes_to_check_stack.append(child)
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

def draw_proc(p, ax, start_angle, depth, colorindex, center=(0.5, 0.5)):
    """Returns the arc and bounds of the drawn wedges.
    Bounds are in the form of (top, left, bottom, right)"""
    try:
        r = 0.1 * (depth + 1)
        color = colors[colorindex]
        p_arc = get_mem_percent_including_children(p) / 100 * 360
        ax.add_artist(Wedge(center, r, start_angle, start_angle + p_arc,
            width=0.1, color=color))

        c_colorindex = get_next_color_index(colorindex)

        ws = WedgeShape(center, start_angle, start_angle + p_arc, r)
        bounds = ws.get_bounds()

        for c in p.get_children():
            cws, c_bounds = draw_proc(c, ax, start_angle, depth + 1, c_colorindex)

            if cws:
                bounds = update_bounds(bounds, c_bounds)
            start_angle += cws.arc
            c_colorindex = get_next_color_index(c_colorindex)

            # can't have a child having the same color as their parent
            # or you can't tell them apart
            while c_colorindex == colorindex:
                c_colorindex = get_next_color_index(c_colorindex)

        return ws, bounds
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
    if colorindex >= len(colors):
        colorindex = 0
    return colorindex
 

def create_graph():
    """The important function: creates a graph of all processes in the system.
    """
    procs = psutil.process_iter()
    fig = plt.figure()
    ax = fig.add_subplot(111)
    center = (0.5, 0.5)

    root_procs = get_root_processes(procs)

    angle_so_far = 0
    colorindex = 0
    bounds = (0.5, 0.5, 0.5, 0.5)
    for p in root_procs:
        ws, bounds2 = draw_proc(p, ax, angle_so_far, 0, colorindex,center)
        bounds = update_bounds(bounds, bounds2)
        angle_so_far += ws.arc
        colorindex = get_next_color_index(colorindex)

    ax.set_xlim(bounds[1], bounds[3])
    ax.set_ylim(bounds[2], bounds[0])

    return fig, ax
