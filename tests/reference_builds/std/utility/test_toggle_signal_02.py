from __future__ import annotations

import unittest
import random

import cohdl
from cohdl import std, Bit, BitVector, Port, Unsigned

from cohdl_testutil import cocotb_util


class test_toggle_signal_02(cohdl.Entity):
    clk = Port.input(Bit)

    reset_toggle = Port.input(Bit)

    first_interval = Port.input(Unsigned[3])
    second_interval = Port.input(Unsigned[3])

    result = Port.output(BitVector[3])
    callback_rising = Port.output(Bit, default=False)
    callback_falling = Port.output(Bit, default=False)

    def architecture(self):
        def on_rising():
            self.callback_rising ^= True

        def on_falling():
            pass
            self.callback_falling ^= True

        ctx = std.Context(std.Clock(self.clk, frequency=std.GHz(2)))

        toggle = std.ToggleSignal(
            ctx,
            self.first_interval,
            self.second_interval,
            on_rising=on_rising,
            on_falling=on_falling,
        )

        std.concurrent_assign(toggle.get_reset_signal(), self.reset_toggle)

        std.concurrent_assign(self.result[0], toggle.state())
        std.concurrent_assign(self.result[1], toggle.rising())
        std.concurrent_assign(self.result[2], toggle.falling())


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
            if self.cnt + 1 >= self.first + self.second:
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
async def testbench_toggle_signal_02(dut: test_toggle_signal_02):
    seq = cocotb_util.SequentialTest(dut.clk)

    dut.first_interval.value = 5
    dut.second_interval.value = 5

    reset = ResetObj(True, dut.reset_toggle)

    callback_rising = False
    callback_falling = False

    def on_rising():
        nonlocal callback_rising
        callback_rising = True

    def on_falling():
        nonlocal callback_falling
        callback_falling = True

    mock = ToggleMock(reset, 5, 5, on_rising=on_rising, on_falling=on_falling)

    async def tick():
        nonlocal callback_rising, callback_falling
        callback_rising = False
        callback_falling = False
        await seq.tick()
        mock.tick(dut.result)

        assert dut.callback_rising.value == callback_rising
        assert dut.callback_falling.value == callback_falling

    def randomize():
        if random.random() < 0.02:
            reset.set(not reset.val)
        if random.random() < 0.05:
            val = random.choice([1, 2, 3, 4, 5, 6, 7])
            dut.first_interval.value = val
            mock.first = val
        if random.random() < 0.05:
            val = random.choice([1, 2, 3, 4, 5, 6, 7])
            dut.second_interval.value = val
            mock.second = val

    await tick()
    await tick()
    reset.set(False)
    await tick()

    for _ in range(2048):
        await tick()
        randomize()


class Unittest(unittest.TestCase):
    def test_toggle_signal_02(self):
        cocotb_util.run_cocotb_tests(test_toggle_signal_02, __file__, self.__module__)
