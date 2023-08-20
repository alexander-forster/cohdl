import unittest

import cohdl
from cohdl import Bit, Port, Unsigned, Variable
from cohdl import std

from cohdl_testutil import cocotb_util


class IntClass:
    def __init__(self, start_val):
        self.val = start_val

    def __iadd__(self, other):
        self.val += other

    def __add__(self, other):
        return IntClass(self.val + other)


class IncOnExit:
    def __init__(self, val):
        self.val = val

    async def __aenter__(self):
        return None

    async def __aexit__(self, a, b, c):
        if cohdl.evaluated():
            self.val @= self.val + 1
        else:
            self.val += 1


async def callback(counter, cond):
    async with IncOnExit(counter):
        if cond == 0:
            return counter + 5

    if cond == 6 or cond == 11:
        if cond == 11:
            async with IncOnExit(counter):
                return counter + 17
        return counter + 4

    async with IncOnExit(counter), IncOnExit(counter):
        if cond == 7 or cond == 8:
            return counter + 11

        if cond == 4:
            return counter + 1

    if cond == 13:
        return counter + 7

    return counter + 13


class test_context_manager_03(cohdl.Entity):
    clk = Port.input(Bit)
    reset = Port.input(Bit)

    condition = Port.input(Unsigned[8])
    result = Port.output(Unsigned[16])
    final_val = Port.output(Unsigned[16])

    def architecture(self):
        var_counter = Variable[Unsigned[16]](0)

        @std.sequential(std.Clock(self.clk), std.Reset(self.reset))
        async def proc():
            var_counter.value = 0
            self.result <<= await callback(var_counter, self.condition)
            self.final_val <<= var_counter


#
# test code
#

import asyncio


@cocotb_util.test()
async def testbench_context_manager_03(dut: test_context_manager_03):
    seq = cocotb_util.SequentialTest(dut.clk)

    dut.reset.value = True
    await seq.tick()
    dut.reset.value = False

    for condition in range(16):
        dut.condition.value = condition
        int_val = IntClass(0)

        loop = asyncio.get_event_loop()
        expected = loop.run_until_complete(callback(int_val, condition))

        await seq.tick()
        await seq.tick()

        assert dut.result.value == expected.val
        assert dut.final_val.value == int_val.val


class Unittest(unittest.TestCase):
    def test_base(self):
        # test, that async-with works when no delay is placed in __aenter__ or __aexit__
        cocotb_util.run_cocotb_tests(test_context_manager_03, __file__, self.__module__)
