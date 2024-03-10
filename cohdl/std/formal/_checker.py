from cohdl import Signal, Bit, pyeval
from cohdl.std._context import sequential

from ._builtins import vhdl, n_prev_true
from ._sequence import _SeqNode, When


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

    def valid_since_reset(self, cnt: int | tuple = 0):
        return n_prev_true(self._past_valid_after_reset, cnt)

    def valid_since_start(self, cnt: int | tuple = 0):
        return n_prev_true(self._past_valid, cnt)

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
            f"{vhdl:{lbl} : assert always {_SeqNode.write_node(cond)};}"
        else:
            f"{vhdl:{lbl} : assert always {_SeqNode.write_node(When(start_guard and reset_guard, cond))};}"

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
            f"{vhdl:{lbl} : assume always {_SeqNode.write_node(cond)};}"
        else:
            f"{vhdl:{label} : assume always {_SeqNode.write_node(When(start_guard and reset_guard, cond))};}"

    def assume_initial(self, label, cond):
        f"{vhdl:{self._complete_label(label)} : assume {_SeqNode.write_node(cond)};}"

    #
    #
    #

    def cover(self, label, cond):
        f"{vhdl:{self._complete_label(label)} : cover <% {_SeqNode.write_node(cond)} %>;}"

    #
    #
    #

    def dbg_show(self, label, signal):
        self.always(label, signal, valid_for=10)

    def fail_after(self, label, cnt):
        self.always(
            label,
            When(self.valid_since_start(cnt - 1), self._always_false),
        )
