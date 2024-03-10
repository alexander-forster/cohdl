from cohdl import pyeval

from ._builtins import vhdl


class _SeqNode:
    @staticmethod
    def write_node(node):
        if isinstance(node, _SeqNode):
            return node.write()
        else:
            return f"{vhdl:{node!r}}"

    def write(self): ...


_write_node = _SeqNode.write_node


class When(_SeqNode):
    @pyeval
    def __init__(self, precond, postcond=None, immediate=True):
        self.precond = precond
        self.postcond = postcond
        self.immediate = immediate

    @pyeval
    def then(self, state, times=None):
        if self.postcond is None:
            self.immediate = True
            self.postcond = State(state, times)
        elif isinstance(self.postcond, Sequence):
            self.postcond.then(state, times)
        else:
            self.postcond = Sequence(self.postcond).then(state, times)
        return self

    @pyeval
    def next(self, state, times=None):
        if self.postcond is None:
            self.immediate = False
            self.postcond = State(state, times)
        elif isinstance(self.postcond, Sequence):
            self.postcond.next(state, times)
        else:
            self.postcond = Sequence(self.postcond).next(state, times)
        return self

    def write(self):
        if self.immediate:
            return (
                f"{vhdl:({_write_node(self.precond)} |-> {_write_node(self.postcond)})}"
            )
        else:
            return (
                f"{vhdl:({_write_node(self.precond)} |=> {_write_node(self.postcond)})}"
            )


class State(_SeqNode):
    def __init__(self, cond, times=None, consecutive=True):
        self.cond = cond
        self.times = times
        self.consecutive = consecutive

    def write_times(self):
        start_char = "*" if self.consecutive else "="

        if self.times is None:
            return ""
        elif isinstance(self.times, tuple):
            if len(self.times) == 0:
                return f"{vhdl:[*]}"
            elif len(self.times) == 1:
                raise AssertionError("not implemented")
            elif len(self.times) == 2:
                return f"{vhdl:[{start_char}{self.times[0]} to {self.times[1]}]}"
            else:
                raise AssertionError("")
        else:
            return f"{vhdl:[->{self.times}]}"

    def write(self):
        return f"{vhdl:{_write_node(self.cond)}{self.write_times()}}"


class Next(State):
    def __init__(self, cond, times=None, consecutive=True):
        super().__init__(cond, times, consecutive)

    def write(self):
        return f"{vhdl: ; {_write_node(self.cond)}{self.write_times()}}"


class Then(State):
    def __init__(self, cond, times=None, consecutive=True):
        super().__init__(cond, times, consecutive)

    def write(self):
        return f"{vhdl: : {_write_node(self.cond)}{self.write_times()}}"


class Wait(State):
    def __init__(self, times=None):
        super().__init__(None, times)

    def write(self):
        return f"{vhdl: ; true {self.write_times()}}"


class Sequence(_SeqNode):
    @staticmethod
    def _write_seq(nodes: list):
        if len(nodes) == 0:
            return ""
        else:
            first, *rest = nodes
            return f"{vhdl:{_write_node(first)}{Sequence._write_seq(rest)}}"

    def __init__(self, start, *seq):
        if isinstance(start, _SeqNode):
            self.start = start
        else:
            self.start = State(start)

        self.seq = [*seq]

    @pyeval
    def then(self, state, times=None, consecutive=True):
        self.seq.append(Then(state, times=times, consecutive=consecutive))
        return self

    @pyeval
    def next(self, state, times=None, consecutive=True):
        self.seq.append(Next(state, times=times, consecutive=consecutive))
        return self

    @pyeval
    def wait(self, times):
        self.seq.append(Wait(times))
        return self

    def write(self):
        return f"{vhdl:<%{_write_node(self.start)}{self._write_seq(self.seq)}%>}"
