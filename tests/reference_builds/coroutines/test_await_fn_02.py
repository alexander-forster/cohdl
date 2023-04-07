from __future__ import annotations

import unittest

import cohdl
from cohdl import std, Bit, Port

from cohdl_testutil import cocotb_util


async def invalid_coroutine(sig):
    raise AssertionError("this is an invalid operation, that cannot be synthesized")


async def wait_for_signal(sig):
    await sig


class test_await_fn_02(cohdl.Entity):
    clk = Port.input(Bit)

    enable = Port.input(Bit)
    input = Port.input(Bit)
    output = Port.output(Bit)

    def architecture(self):
        clk = std.Clock(self.clk)

        @std.sequential(clk)
        async def proc_simple():
            # invalid coroutine is not converted
            # when it is not awaited
            invalid_coroutine(self.enable)
            await wait_for_signal(self.enable)
            self.output <<= self.input


#
# test code
#


@cocotb_util.test()
async def testbench_await_fn_02(dut: test_await_fn_02):
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
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_await_fn_02, __file__, self.__module__)
