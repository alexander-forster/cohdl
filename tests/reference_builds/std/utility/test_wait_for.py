from __future__ import annotations

import unittest

import cohdl
from cohdl import std, Bit, Port, Signal, Unsigned

from cohdl_testutil import cocotb_util


class test_wait_for(cohdl.Entity):
    clk = Port.input(Bit)

    start = Port.input(Bit)
    var_wait = Port.input(Unsigned[5])

    output_a = Port.output(Bit)
    output_b = Port.output(Bit)
    output_c = Port.output(Bit)

    output_waiter_a = Port.output(Bit)
    output_waiter_b = Port.output(Bit)
    output_waiter_c = Port.output(Bit)

    def architecture(self):
        raw_clk = std.Clock(self.clk)
        timed_clk = std.Clock(self.clk, frequency=std.GHz(1))

        zero_val = Signal[Unsigned[3]](0)

        @std.SequentialContext(raw_clk)
        async def proc_raw():
            await self.start
            self.output_a <<= True
            await std.wait_for(1)
            self.output_a <<= False
            await std.wait_for(2)
            self.output_a <<= True
            await std.wait_for(5)
            self.output_a <<= False

        @std.sequential(timed_clk)
        async def proc_timed():
            await self.start
            self.output_b <<= True
            await std.wait_for(std.ns(1))
            self.output_b <<= False
            await std.wait_for(std.ps(2000))
            self.output_b <<= True
            await std.wait_for(std.us(0.005))
            self.output_b <<= False

        @std.sequential(raw_clk)
        async def proc_var():
            await self.start
            self.output_c <<= True
            await std.wait_for(self.var_wait)
            self.output_c <<= False
            await std.wait_for(self.var_wait)
            await std.wait_for(zero_val, allow_zero=True)
            self.output_c <<= True
            await std.wait_for(self.var_wait)
            self.output_c <<= False

        waiter_a = std.Waiter(5)

        @std.SequentialContext(raw_clk)
        async def proc_waiter_raw():
            await self.start
            self.output_waiter_a <<= True
            await waiter_a.wait_for(1)
            self.output_waiter_a <<= False
            await waiter_a.wait_for(2)
            self.output_waiter_a <<= True
            await waiter_a.wait_for(5)
            self.output_waiter_a <<= False

        waiter_b = std.Waiter(std.us(0.005))

        @std.sequential(timed_clk)
        async def proc_waiter_timed():
            await self.start
            self.output_waiter_b <<= True
            await waiter_b.wait_for(std.ns(1))
            self.output_waiter_b <<= False
            await waiter_b.wait_for(std.ps(2000))
            self.output_waiter_b <<= True
            await waiter_b.wait_for(std.us(0.005))
            self.output_waiter_b <<= False

        waiter_c = std.Waiter(31)

        @std.sequential(raw_clk)
        async def proc_var():
            await self.start
            self.output_waiter_c <<= True
            await waiter_c.wait_for(self.var_wait)
            self.output_waiter_c <<= False
            await waiter_c.wait_for(self.var_wait)
            await waiter_c.wait_for(zero_val, allow_zero=True)
            self.output_waiter_c <<= True
            await waiter_c.wait_for(self.var_wait)
            self.output_waiter_c <<= False


#
# test code
#


@cocotb_util.test()
async def testbench_wait_for(dut: test_wait_for):
    seq = cocotb_util.SequentialTest(dut.clk)
    dut.start.value = 0

    async def wait_and_check(*states):
        for s in states:
            await seq.tick()
            assert dut.output_a.value == s
            assert dut.output_b.value == s
            assert dut.output_c.value == s

            assert dut.output_waiter_a.value == s
            assert dut.output_waiter_b.value == s
            assert dut.output_waiter_c.value == s

    await seq.tick()
    dut.start.value = 1
    dut.var_wait.value = 1
    await wait_and_check(1)
    dut.start.value = 0
    dut.var_wait.value = 2
    await wait_and_check(0, 0)
    dut.var_wait.value = 5
    await wait_and_check(1, 1, 1, 1, 1)
    await wait_and_check(0, 0, 0, 0, 0)


class Unittest(unittest.TestCase):
    def test_wait_for(self):
        cocotb_util.run_cocotb_tests(test_wait_for, __file__, self.__module__)
