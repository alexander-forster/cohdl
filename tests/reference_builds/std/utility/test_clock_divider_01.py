from __future__ import annotations

import unittest
import random

import cohdl
from cohdl import std, Bit, BitVector, Port

from cohdl_testutil import cocotb_util


class test_clock_divider_01(cohdl.Entity):
    clk = Port.input(Bit)
    enable = Port.input(Bit)

    a = Port.output(BitVector[3])
    b = Port.output(BitVector[3])
    c = Port.output(BitVector[3])
    d = Port.output(BitVector[3])
    e = Port.output(BitVector[3])
    f = Port.output(BitVector[3])
    g = Port.output(BitVector[3])
    h = Port.output(BitVector[3])
    i = Port.output(BitVector[3])
    j = Port.output(BitVector[3])

    dbg = Port.input(BitVector[3])

    callback_rising = Port.output(Bit, default=False)
    callback_falling = Port.output(Bit, default=False)

    def architecture(self):
        def on_rising():
            self.callback_rising ^= True

        def on_falling():
            self.callback_falling ^= True

        ctx = std.SequentialContext(std.Clock(self.clk, frequency=std.GHz(1)))

        a = std.ClockDivider(ctx, std.ns(2))
        b = std.ClockDivider(ctx, 5, on_rising=on_rising, on_falling=on_falling)
        c = std.ClockDivider(ctx, 5, default_state=True)
        d = std.ClockDivider(ctx, 5, tick_at_start=True)
        e = std.ClockDivider(ctx, 5, default_state=True, tick_at_start=True)
        f = std.ClockDivider(ctx, 5, require_enable=True)
        g = std.ClockDivider(ctx, 5, default_state=True, require_enable=True)
        h = std.ClockDivider(ctx, 5, tick_at_start=True, require_enable=True)
        i = std.ClockDivider(ctx, 2)
        j = std.ClockDivider(ctx, 2, default_state=True)

        toggle_list = [a, b, c, d, e, f, g, h, i, j]
        port_list = [
            self.a,
            self.b,
            self.c,
            self.d,
            self.e,
            self.f,
            self.g,
            self.h,
            self.i,
            self.j,
        ]

        @std.sequential(ctx.clk().falling())
        def logic_enable_f():
            if self.enable:
                f.enable()
                g.enable()
                h.enable()
            else:
                f.disable()
                g.disable()
                h.disable()

        for toggle, port in zip(toggle_list, port_list):

            @std.concurrent
            def logic():
                port[0] <<= toggle.state()
                port[1] <<= toggle.rising()
                port[2] <<= toggle.falling()


#
# test code
#


class MockClkDivider:
    def __init__(
        self,
        signal,
        duration,
        default_state,
        tick_at_start,
        *,
        require_enable=False,
        on_rising=std.nop,
        on_not_rising=std.nop,
        on_falling=std.nop,
        on_not_falling=std.nop,
    ):
        self._signal = signal
        self._duration = duration
        self._default_state = default_state
        self._tick_at_start = tick_at_start
        self._require_enable = require_enable
        self._state = default_state
        self._on_rising = on_rising
        self._on_not_rising = on_not_rising
        self._on_falling = on_falling
        self._on_not_falling = on_not_falling
        self.dbg = 0

        self._last_enable = 0

    def step(self, nr: int, en: bool):
        if self._require_enable:
            if not en:
                self._last_enable = nr
                assert self._signal.value == self._default_state
                return

            if self._last_enable:
                nr = nr - self._last_enable - 1

        if not self._tick_at_start:
            if nr % self._duration == self._duration - 1:
                state = not self._default_state
            else:
                state = self._default_state
        else:
            if nr % self._duration == 0:
                state = not self._default_state
            else:
                state = self._default_state

        if state != self._state:
            rising = state
            falling = not state
        else:
            rising = False
            falling = False

        if rising:
            self._on_rising()
        else:
            self._on_not_rising()

        if falling:
            self._on_falling()
        else:
            self._on_not_falling()

        self._state = state

        expected = state | (rising << 1) | (falling << 2)
        self.dbg = expected

        assert self._signal.value == expected


@cocotb_util.test()
async def testbench_clock_divider_01(dut: test_clock_divider_01):
    dut.clk.value = False
    dut.enable.value = False
    await cocotb_util.step()
    seq = cocotb_util.SequentialTest(dut.clk)

    def val_checker(val, expected):
        def checker():
            assert val.value == expected

        return checker

    mock_list = [
        MockClkDivider(dut.a, 2, False, False),
        MockClkDivider(
            dut.b,
            5,
            False,
            False,
            on_rising=val_checker(dut.callback_rising, True),
            on_not_rising=val_checker(dut.callback_rising, False),
        ),
        MockClkDivider(dut.c, 5, True, False),
        MockClkDivider(dut.d, 5, False, True),
        MockClkDivider(dut.e, 5, True, True),
        MockClkDivider(dut.f, 5, False, False, require_enable=True),
        MockClkDivider(dut.g, 5, True, False, require_enable=True),
        MockClkDivider(dut.h, 5, False, tick_at_start=True, require_enable=True),
        MockClkDivider(dut.i, 2, False, False),
        MockClkDivider(dut.j, 2, True, False),
    ]

    for nr in range(256):
        en = 60 < nr < 150
        dut.enable.value = en

        await seq.tick()

        for m in mock_list:
            m.step(nr, en)
            dut.dbg.value = m.dbg


class Unittest(unittest.TestCase):
    def test_clock_divider_01(self):
        cocotb_util.run_cocotb_tests(test_clock_divider_01, __file__, self.__module__)
