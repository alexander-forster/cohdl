from __future__ import annotations

import cohdl
from cohdl import Signal, Bit, Unsigned, BitVector


class SeqContext:
    def __init__(self, clk: cohdl.std.Clock, reset: cohdl.std.Reset | None = None):
        self.clk = clk
        self.reset = reset

    def __call__(self, fn):
        cohdl.std.sequential(self.clk, self.reset)(fn)

    def signal_falling(self, sig: Signal[Bit]):
        out = Signal[Bit](False)
        prev = Signal[Bit](False)

        @cohdl.std.sequential(self.clk, self.reset)
        def proc_signal_falling():
            prev.next = sig

            if prev and not sig:
                out.next = True
            else:
                out.next = False

        return out

    def signal_rising(self, sig: Signal[Bit]):
        out = Signal[Bit](False)
        prev = Signal[Bit](False)

        @cohdl.std.sequential(self.clk, self.reset)
        def proc_signal_rising():
            prev.next = sig

            if not prev and sig:
                out.next = True
            else:
                out.next = False

        return out

    def true_for(self, clk_cnt: int, cond):
        if isinstance(cond, cohdl.Signal):
            cond_fn = lambda: cond
        else:
            cond_fn = cond

        cnt = Signal[Unsigned.upto(clk_cnt)](clk_cnt)

        @cohdl.std.sequential(self.clk, self.reset)
        def proc_true_for():
            if cond_fn():
                if cnt:
                    cnt.next = cnt - 1
            else:
                cnt.next = clk_cnt

        out = Signal[Bit](False)

        @cohdl.std.concurrent
        def logic_true_for():
            out.next = cnt == 0

        return out

    def interval(self, cnt: int):
        out = Signal[Bit](False)
        interval_cnt = Signal[Unsigned.upto(cnt)](cnt - 1)

        @cohdl.std.concurrent
        def logic():
            out.next = interval_cnt == 0

        @cohdl.std.sequential(self.clk, self.reset)
        def proc_interval():
            if interval_cnt == 0:
                interval_cnt.next = cnt - 1
            else:
                interval_cnt.next = interval_cnt - 1

        return out

    def moving_average(
        self,
        signal,
        sample_cnt,
        default=False,
    ):
        from cohdl import std

        assert not cohdl.evaluated()

        out = Signal[Bit](default)
        counter = Signal[Unsigned.upto(sample_cnt)](
            0 if default is False else sample_cnt
        )

        @std.sequential(self.clk, self.reset)
        def proc_moving_average():
            if signal:
                if counter != sample_cnt:
                    counter.next = counter + 1
                else:
                    out.next = True
            else:
                if counter != 0:
                    counter.next = counter - 1
                else:
                    out.next = False

        return out
