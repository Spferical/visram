import psutil


def generate_process_graph():
    """
    Returns a process graph of all the processes in the system.
    """
    return ProcessGraph(psutil.process_iter())


class ProcessGraph(object):

    def __init__(self, processes):
        self.snapshots = {}
        self.root_pids = []
        self.child_map = {}
        self.mem_percents_including_children = {}
        self._update_process_dicts(processes)
        self._update_process_children_map()
        self._get_percents_including_children()
        self._update_root_pids()

    def _update_process_dicts(self, processes):
        """Creates a dict of the dicts of each process on the system.
        Probably faster than calling p.get_whatever() many times, and, rather
        importantly, gives a /snapshot/ of the system's processes at a certain
        time.
        """
        self.p_dicts = {}
        for process in processes:
            self._snapshot_process(process)

    def get_percent_including_children(self, pid):
        """Gets the percent of RAM a process is using, including that used by
        all of its children."""
        if pid in self.mem_percents_including_children:
            return self.mem_percents_including_children[pid]
        try:
            pids_to_check_stack = []
            pids_to_check_stack.append(pid)
            total_percent = 0
            while pids_to_check_stack:
                pid = pids_to_check_stack.pop()
                try:
                    total_percent += self.p_dicts[pid]['memory_percent']
                    for child in self.child_map[pid]:
                        pids_to_check_stack.append(child)
                except KeyError:
                    # processes are pretty unstable
                    # and may not have been put in child_map or p_dicts
                    pass
            self.mem_percents_including_children[pid] = total_percent
            return total_percent
        except psutil.NoSuchProcess:
            return 0

    def _update_root_pids(self):
        """Gets pids of all processes in p_dicts that have no parents."""
        self.root_pids = []
        for pid, p_dict in self.p_dicts.items():
            parent_pid = p_dict['parent']
            # processes without parents are root processes
            # WORKAROUND FOR OSX: pid 0's parent is itself, so we need to check
            # if a process's parent is itself
            if parent_pid is None or parent_pid == pid:
                self.root_pids.append(pid)

    def _update_process_children_map(self):
        """Creates a dict of the children of each process in the system.
        This is way way way faster than calling psutil.get_children()
        each time we want to iterate on a process's children.
        Indexed by process PID.
        """

        # create a list for each process
        for pid in self.p_dicts:
            self.child_map[pid] = []

        # add each process to its parent's child list
        for pid, p_dict in self.p_dicts.items():
            parent_pid = p_dict['parent']
            # in OSX, the process with PID=0 is it's own parent.
            # We need to check for recursive relationships like this to
            # prevent infinite recursion.
            if parent_pid is not None and parent_pid != pid:
                self.child_map[parent_pid].append(pid)

    def _snapshot_process(self, process):
        try:
            p = process.as_dict(
                attrs=['pid', 'name', 'memory_percent', 'cpu_percent',
                       'username', 'memory_info'])
            parent = process.parent()
            p['parent'] = parent.pid if parent is not None else None
            self.p_dicts[p['pid']] = p
        except psutil.NoSuchProcess:
            self._snapshot_process(process)

    def _get_percents_including_children(self):
        for pid in self.p_dicts:
            # call it so the value gets cached
            self.get_percent_including_children(pid)

    def get_name(self, pid):
        return self.p_dicts[pid]['name']

    def get_memory_percent(self, pid):
        return self.p_dicts[pid]['memory_percent']

    def get_cpu_percent(self, pid):
        return self.p_dicts[pid]['cpu_percent']

    def get_username(self, pid):
        return self.p_dicts[pid]['username']

    def get_memory_info(self, pid):
        return self.p_dicts[pid]['memory_info']

    def get_parent_pid(self, pid):
        return self.p_dicts[pid]['parent']

    def get_child_pids(self, pid):
        return self.child_map[pid]

    def get_root_pids(self):
        return self.root_pids
