from __future__ import annotations

import unittest
import random

import cohdl
from cohdl import std, Bit, BitVector, Port

from cohdl_testutil import cocotb_util


class test_toggle_signal_01(cohdl.Entity):
    clk = Port.input(Bit)

    reset_toggle = Port.input(Bit)

    a = Port.output(BitVector[3])
    b = Port.output(BitVector[3])
    c = Port.output(BitVector[3])
    d = Port.output(BitVector[3])
    e = Port.output(BitVector[3])
    f = Port.output(BitVector[3])
    g = Port.output(BitVector[3])
    h = Port.output(BitVector[3])
    i = Port.output(BitVector[3])

    callback_rising = Port.output(Bit, default=False)
    callback_falling = Port.output(Bit, default=False)

    def architecture(self):
        def on_rising():
            self.callback_rising ^= True

        def on_falling():
            self.callback_falling ^= True

        ctx = std.SequentialContext(std.Clock(self.clk, frequency=std.GHz(2)))

        a = std.ToggleSignal(ctx, std.ns(2))
        b = std.ToggleSignal(ctx, std.ns(2), std.ns(1))
        c = std.ToggleSignal(ctx, 5)
        d = std.ToggleSignal(ctx, 1, 1)
        e = std.ToggleSignal(ctx, 1, 0)
        f = std.ToggleSignal(ctx, 0, 1)
        g = std.ToggleSignal(ctx, std.ns(5), default_state=True)
        h = std.ToggleSignal(ctx, std.ns(5), first_state=True)
        i = std.ToggleSignal(ctx, std.ns(5), on_rising=on_rising, on_falling=on_falling)

        toggle_list = [a, b, c, d, e, f, g, h, i]
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
        ]

        for toggle, port in zip(toggle_list, port_list):
            std.concurrent_assign(toggle.get_reset_signal(), self.reset_toggle)

            std.concurrent_assign(port[0], toggle.state())
            std.concurrent_assign(port[1], toggle.rising())
            std.concurrent_assign(port[2], toggle.falling())


#
# test code
#


class ToggleMock:
    def __init__(
        self,
        reset: bool,
        first: int,
        second: int,
        default_state=False,
        first_state=False,
        on_rising=std.nop,
        on_falling=std.nop,
    ):
        self.reset = reset
        self.first = first
        self.second = second
        self.default = default_state
        self.first_state = first_state
        self.on_rising = on_rising
        self.on_falling = on_falling

        self.cnt = -1
        self.prev_state = default_state
        self.state = default_state
        self.rising = False
        self.falling = False

        self.rst = bool(reset)

    def tick(self, expected):
        self.rising = False
        self.falling = False
        self.prev_state = self.state
        p = self.cnt

        if self.reset:
            self.cnt = 0
            self.prev_state = self.default
            self.state = self.default
        else:
            if self.cnt + 1 == self.first + self.second:
                self.cnt = 0
            else:
                self.cnt = self.cnt + 1

            if self.cnt < self.first:
                self.state = self.first_state
            else:
                self.state = not self.first_state

            if self.prev_state != self.state:
                if self.prev_state:
                    self.on_falling()
                    self.falling = True
                else:
                    self.on_rising()
                    self.rising = True

        self.rst = bool(self.reset)
        self.check(expected)

    def check(self, inp):
        val = inp.value

        assert bool(val & 1) == self.state
        assert bool(val & 2) == self.rising
        assert bool(val & 4) == self.falling


class ResetObj:
    def __init__(self, initial=True, port=None):
        self.val = initial
        self.port = port
        port.value = initial

    def set(self, val):
        self.val = val
        self.port.value = val

    def __bool__(self):
        return bool(self.val)


@cocotb_util.test()
async def testbench_toggle_signal_01(dut: test_toggle_signal_01):
    seq = cocotb_util.SequentialTest(dut.clk)

    reset = ResetObj(True, dut.reset_toggle)

    callback_rising = False
    callback_falling = False

    def on_rising():
        nonlocal callback_rising
        callback_rising = True

    def on_falling():
        nonlocal callback_falling
        callback_falling = True

    a = ToggleMock(reset, 4, 4)
    b = ToggleMock(reset, 4, 2)
    c = ToggleMock(reset, 5, 5)
    d = ToggleMock(reset, 1, 1)
    e = ToggleMock(reset, 1, 0)
    f = ToggleMock(reset, 0, 1)
    g = ToggleMock(reset, 10, 10, default_state=True)
    h = ToggleMock(reset, 10, 10, first_state=True)
    i = ToggleMock(reset, 10, 10, on_rising=on_rising, on_falling=on_falling)

    async def tick():
        nonlocal callback_rising, callback_falling
        callback_rising = False
        callback_falling = False
        await seq.tick()
        a.tick(dut.a)
        b.tick(dut.b)
        c.tick(dut.c)
        d.tick(dut.d)
        e.tick(dut.e)
        f.tick(dut.f)
        g.tick(dut.g)
        h.tick(dut.h)
        i.tick(dut.i)

        assert dut.callback_rising.value == callback_rising
        assert dut.callback_falling.value == callback_falling

    def random_reset():
        if random.random() < 0.02:
            reset.set(not reset.val)

    for _ in range(1024):
        await tick()
        random_reset()


class Unittest(unittest.TestCase):
    def test_toggle_signal_01(self):
        cocotb_util.run_cocotb_tests(test_toggle_signal_01, __file__, self.__module__)
