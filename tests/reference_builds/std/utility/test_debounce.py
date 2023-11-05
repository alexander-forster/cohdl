from __future__ import annotations

import unittest
import random

import cohdl
from cohdl import std, Bit, BitVector, Unsigned, Port, Null, Full, Signal

from cohdl_testutil import cocotb_util
from collections import deque


class test_debounce(cohdl.Entity):
    clk = Port.input(Bit)
    input = Port.input(Bit)

    debounce_0 = Port.output(Bit)
    debounce_1 = Port.output(Bit)
    debounce_2 = Port.output(Bit)
    debounce_3 = Port.output(Bit)
    debounce_4 = Port.output(Bit)
    debounce_5 = Port.output(Bit)
    debounce_6 = Port.output(Bit)

    def architecture(self):
        ctx = std.SequentialContext(std.Clock(self.clk, frequency=std.GHz(1)))
        ca = std.concurrent_assign

        ca(self.debounce_0, std.debounce(ctx, self.input, 10))
        ca(self.debounce_1, std.debounce(ctx, self.input, 10, initial=True))
        ca(self.debounce_2, std.debounce(ctx, self.input, 1))
        ca(self.debounce_3, std.debounce(ctx, self.input, 1, initial=True))
        ca(self.debounce_4, std.debounce(ctx, self.input, std.ns(20)))
        ca(self.debounce_5, std.debounce(ctx, self.input, std.ps(11000), initial=True))
        ca(self.debounce_6, std.debounce(ctx, self.input, std.us(0.009), initial=True))


#
# test code
#


class MockDebounce:
    def __init__(self, initial: bool, max_count: int, signal):
        self._max = max_count
        self._cnt = max_count // 2
        self._val = initial
        self._signal = signal

    def update(self, inp):
        if inp:
            if self._cnt == self._max:
                self._val = True

            self._cnt = min(self._cnt + 1, self._max)
        else:
            if self._cnt == 0:
                self._val = False

            self._cnt = max(self._cnt - 1, 0)

        assert self._signal.value == self._val

        return self._val


@cocotb_util.test()
async def testbench_debounce(dut: test_debounce):
    tested = [
        MockDebounce(False, 10, dut.debounce_0),
        MockDebounce(True, 10, dut.debounce_1),
        MockDebounce(False, 1, dut.debounce_2),
        MockDebounce(True, 1, dut.debounce_3),
        MockDebounce(False, 20, dut.debounce_4),
        MockDebounce(True, 11, dut.debounce_5),
        MockDebounce(True, 9, dut.debounce_6),
    ]

    dut.clk.value = False
    dut.input.value = False
    await cocotb_util.step()
    await cocotb_util.step()

    async def update(val):
        dut.input.value = val
        dut.clk.value = True
        await cocotb_util.step()
        await cocotb_util.step()

        dut.clk.value = False
        await cocotb_util.step()
        await cocotb_util.step()

        for t in tested:
            t.update(val)

    for _ in range(50):
        await update(True)

    for _ in range(50):
        await update(False)

    await update(True)

    for nr in range(10):
        await update(nr % 2 == 0)

    for _ in range(500):
        await update(random.choice([True, False]))


class Unittest(unittest.TestCase):
    def test_hdl(self):
        cocotb_util.run_cocotb_tests(test_debounce, __file__, self.__module__)
