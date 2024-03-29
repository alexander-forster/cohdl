from __future__ import annotations

import unittest

import cohdl
from cohdl import std, Bit, Port

from cohdl_testutil import cocotb_util


class test_await_01(cohdl.Entity):
    clk = Port.input(Bit)

    enable = Port.input(Bit)
    input = Port.input(Bit)
    output = Port.output(Bit)

    def architecture(self):
        clk = std.Clock(self.clk)

        @std.sequential(clk)
        async def proc_simple():
            std.comment(
                "test comment to check if it affects empty state before first await"
            )
            cohdl.comment(
                "test comment to check if it affects empty state before first await"
            )
            std.comment(
                "test comment to check if it affects empty state before first await"
            )
            cohdl.comment(
                "test comment to check if it affects empty state before first await"
            )
            await self.enable
            self.output <<= self.input


#
# test code
#


@cocotb_util.test()
async def testbench_await_01(dut: test_await_01):
    seq = cocotb_util.SequentialTest(dut.clk)

    async def test(enable, inp, expected):
        cocotb_util.assign(dut.input, inp)
        cocotb_util.assign(dut.enable, enable)
        await seq.tick()
        await seq.tick()
        assert dut.output == expected

    await test(1, 0, 0)
    await test(1, 1, 1)
    await test(0, 0, 1)
    await test(0, 1, 1)
    await test(1, 0, 0)
    await test(0, 0, 0)


class Unittest(unittest.TestCase):
    def test_await_01(self):
        cocotb_util.run_cocotb_tests(test_await_01, __file__, self.__module__)
