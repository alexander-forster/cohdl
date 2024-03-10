from __future__ import annotations

from cohdl import vhdl, Bit, Signal
from cohdl import vhdl as raw_vhdl
from ._context import sequential

from cohdl import pyeval, Attribute

#
# inline vhdl
#


class vhdl(raw_vhdl):
    def post_process(self, text: str):
        result = text.replace("<%", "{")
        return result.replace("%>", "}")


#
# attributes
#


class anyconst(Attribute, type=bool): ...


#
#
#


class ConfigFormal:
    disable_cover = True
    disable_assert = True
    disable_assume = True


#
#
#


def conv(inp):
    if isinstance(inp, Formal):
        return inp.write()
    else:
        return f"{vhdl:{inp!r}}"


def conv_seq(s):
    if len(s) == 0:
        return f"{vhdl:}"
    else:
        first, *rest = s
        return f"{vhdl:{first.write()}{conv_seq(rest)}}"


#
#
#


class Formal:
    def write(self): ...


class When(Formal):
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
            return f"{vhdl:({conv(self.precond)} |-> {conv(self.postcond)})}"
        else:
            return f"{vhdl:({conv(self.precond)} |=> {conv(self.postcond)})}"


class State(Formal):
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
        return f"{vhdl:{conv(self.cond)}{self.write_times()}}"


class Next(State):
    def __init__(self, cond, times=None, consecutive=True):
        super().__init__(cond, times, consecutive)

    def write(self):
        return f"{vhdl: ; {conv(self.cond)}{self.write_times()}}"


class Then(State):
    def __init__(self, cond, times=None, consecutive=True):
        super().__init__(cond, times, consecutive)

    def write(self):
        return f"{vhdl: : {conv(self.cond)}{self.write_times()}}"


class Wait(State):
    def __init__(self, times=None):
        super().__init__(None, times)

    def write(self):
        return f"{vhdl: ; true {self.write_times()}}"


class Sequence(Formal):
    def __init__(self, start, *seq):
        if isinstance(start, Formal):
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
        return f"{vhdl:<%{conv(self.start)}{conv_seq(self.seq)}%>}"


def stable(arg):
    return f"{vhdl[bool]:stable({arg!r})}"


def prev(state, cnt=None):
    if cnt is None:
        return f"{vhdl[state.type]:prev({state!r})}"
    else:
        return f"{vhdl[state.type]:prev({state!r}, {cnt})}"


class PrevCache:
    caches = {}

    def __init__(self, signal):
        self.signal = signal
        self.cache = {}
        self.cache_exact = {}

    @pyeval
    def get(self, cnt):
        return self.cache.get(cnt, None)

    @pyeval
    def get_exact(self, cnt):
        return self.cache_exact.get(cnt, None)

    @pyeval
    def add(self, cnt, signal):
        self.cache[cnt] = signal

    @pyeval
    def add_exact(self, cnt, signal):
        self.cache_exact[cnt] = signal

    @staticmethod
    @pyeval
    def get_cache(signal) -> PrevCache:
        for key, val in PrevCache.caches.items():
            if key == id(signal):
                return val

        new_cache = PrevCache(signal)
        PrevCache.caches[id(signal)] = new_cache
        return new_cache


def all_prev(state, cnt: int, *, exact=False):
    cache = PrevCache.get_cache(state)

    cached = cache.get(cnt)

    if cached is None:
        if cnt == 0:
            cache.add(cnt, state)
        else:
            cache.add(cnt, all_prev(state, cnt - 1) & prev(state, cnt))

    if exact:
        cached_exact = cache.get_exact(cnt)

        if cached_exact is None:
            cache.add_exact(cnt, cache.get(cnt) & ~prev(state, cnt + 1))

        return cache.get_exact(cnt)
    else:
        return cache.get(cnt)


class Checker:
    def __init__(self, clk, reset=None, *, prefix: str | None = None):
        self._always_false = Signal[Bit](False, name="always_false")
        self._past_valid = Signal[Bit](False, name="past_exists")
        self._past_valid_after_reset = Signal[Bit](False, name="past_valid_after_reset")
        self._clk = clk
        self._reset = reset
        self._prefix = prefix

        @sequential(clk, reset)
        def proc():
            self._past_valid_after_reset <<= True

        @sequential(clk)
        def proc():
            self._past_valid <<= True

    @pyeval
    def _complete_label(self, label):
        if self._prefix is not None:
            return f"{self._prefix}{label}"
        return label

    def valid_since_reset(self, cnt: int | None = None, *, exact=False):
        if cnt is None:
            return self._past_valid_after_reset
        else:
            return all_prev(self._past_valid_after_reset, cnt, exact=exact)

    def valid_since_start(self, cnt: int | None = None, *, exact=False):
        if cnt is None:
            return self._past_valid
        else:
            return all_prev(self._past_valid, cnt, exact=exact)

    def always(
        self,
        label,
        cond,
        *,
        since_start=None,
        since_reset=None,
    ):
        lbl = self._complete_label(label)

        if since_start is None:
            start_guard = True
        else:
            start_guard = self.valid_since_start(since_start)

        if since_reset is None:
            reset_guard = True
        else:
            reset_guard = self.valid_since_reset(since_reset)

        if start_guard is True and reset_guard is True:
            f"{vhdl:{lbl} : assert always {conv(cond)};}"
        else:
            f"{vhdl:{lbl} : assert always {conv(When(start_guard and reset_guard, cond))};}"

    #
    #
    #

    def assume_always(
        self,
        label,
        cond,
        *,
        since_start=None,
        since_reset=None,
    ):
        lbl = self._complete_label(label)

        if since_start is None:
            start_guard = True
        else:
            start_guard = self.valid_since_start(since_start)

        if since_reset is None:
            reset_guard = True
        else:
            reset_guard = self.valid_since_reset(since_reset)

        if start_guard is True and reset_guard is True:
            f"{vhdl:{lbl} : assume always {conv(cond)};}"
        else:
            f"{vhdl:{label} : assume always {conv(When(start_guard and reset_guard, cond))};}"

    def assume_initial(self, label, cond):
        f"{vhdl:{self._complete_label(label)} : assume {conv(cond)};}"

    #
    #
    #

    def cover(self, label, cond):
        f"{vhdl:{self._complete_label(label)} : cover <% {conv(cond)} %>;}"

    #
    #
    #

    def dbg_show(self, label, signal):
        self.always(label, signal, valid_for=10)

    def fail_after(self, label, cnt):
        self.always(
            self._complete_label(label),
            When(self.valid_since_start(cnt - 1), self._always_false),
        )
