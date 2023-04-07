from __future__ import annotations

import cohdl
from cohdl import Bit, Signal, Unsigned

from ._context import sequential, concurrent


def moving_average(
    clk,
    reset,
    signal,
    sample_cnt,
    default=False,
):
    assert not cohdl.evaluated

    out = Signal(Bit, False)
    counter = Signal(
        Unsigned[sample_cnt.bit_length()], 0 if default is False else sample_cnt
    )

    @std.sequential(clk, reset)
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


def duty_cycle(clk, reset, count: int, duty: float):
    on_count = int(count * duty)
    counter = Signal(Unsigned[count.bit_length()], 0)

    out = Signal(Bit, False)

    @concurrent
    def logic_duty_cycle():
        out.next = counter < on_count

    @sequential(clk, reset)
    def proc_duty_cycle():
        if counter != count:
            counter.next = counter + 1
        else:
            counter.next = 0

    return out


class Prescaler:
    def __init__(self, clk, reset, reload: int):
        self._tick = Signal(Bit, False, name="prescaler_tick")
        self._reset_counter = Signal(Bit, False, name="prescaler_reset")
        self._counter = Signal(
            Unsigned[reload.bit_length()], reload, name="prescaler_cnt"
        )

        @sequential(clk, reset)
        def proc_prescaler():
            if self._reset_counter:
                self._counter <<= reload
            else:
                if self._counter == 0:
                    self._counter <<= reload
                    self._tick ^= True
                else:
                    self._counter <<= self._counter - 1

    def reset(self):
        self._reset_counter ^= True

    def tick(self):
        return self._tick


class ClockDivider:
    def __init__(self, clk, reset, factor: int):
        assert factor % 2 == 0

        self._clk = clk
        self._reset = reset

        self._prev = Signal(Bit, False)
        self._current = Signal(Bit, False)

        reload = (factor // 2) - 1

        counter = Signal(Unsigned[reload.bit_length()], reload)

        @sequential(clk, reset)
        def proc_clock_divider_prev():
            self._prev <<= self._current

        @sequential(clk, reset)
        async def proc_clock_divider():
            if counter:
                counter.next = counter - 1
            else:
                counter.next = reload
                self._current <<= ~self._current

    def high(self):
        return self._current

    def low(self):
        return ~self._current

    def rising(self):
        return ~self._prev & self._current

    def falling(self):
        return self._prev & ~self._current
