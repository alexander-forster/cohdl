from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, Port, Unsigned

from cohdl import std

from cohdl_testutil import cocotb_util
from cocotb.triggers import Timer

gen = cocotb_util.ConstrainedGenerator


class test_boolean_03(cohdl.Entity):
    clk = Port.input(Bit)

    cnt_1_rising = Port.output(Unsigned[8], default=0)
    cnt_1_falling = Port.output(Unsigned[8], default=0)
    cnt_1_both = Port.output(Unsigned[8], default=0)

    cnt_2_rising = Port.output(Unsigned[8], default=0)
    cnt_2_falling = Port.output(Unsigned[8], default=0)
    cnt_2_both = Port.output(Unsigned[8], default=0)

    def architecture(self):
        @cohdl.sequential_context
        def proc_rising_1():
            if cohdl.rising_edge(self.clk):
                self.cnt_1_rising <<= self.cnt_1_rising + 1

        @cohdl.sequential_context
        def proc_falling_1():
            if cohdl.falling_edge(self.clk):
                self.cnt_1_falling <<= self.cnt_1_falling + 1

        @cohdl.sequential_context
        def proc_both_1():
            if cohdl.rising_edge(self.clk) | cohdl.falling_edge(self.clk):
                self.cnt_1_both <<= self.cnt_1_both + 1

        clk = std.Clock(self.clk)

        @std.sequential(clk.rising())
        def proc_rising_2():
            self.cnt_2_rising <<= self.cnt_2_rising + 1

        @std.sequential(clk.falling())
        def proc_falling_2():
            self.cnt_2_falling <<= self.cnt_2_falling + 1

        @std.sequential(clk.both())
        def proc_both_2():
            self.cnt_2_both <<= self.cnt_2_both + 1


#
# test code
#


@cocotb_util.test()
async def testbench_boolean_03(dut: test_boolean_03):
    rising = 0
    falling = 0

    def check():
        both = rising + falling

        assert cocotb_util.compare(dut.cnt_1_rising, rising)
        assert cocotb_util.compare(dut.cnt_2_rising, rising)
        assert cocotb_util.compare(dut.cnt_1_falling, falling)
        assert cocotb_util.compare(dut.cnt_2_falling, falling)
        assert cocotb_util.compare(dut.cnt_1_both, both)
        assert cocotb_util.compare(dut.cnt_2_both, both)

    dut.clk.value = False
    await Timer(1, units="ns")

    for _ in range(10):
        dut.clk.value = True
        await Timer(1, units="ns")
        rising += 1
        check()

        dut.clk.value = False
        await Timer(1, units="ns")
        falling += 1
        check()


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_boolean_03, __file__, self.__module__)
