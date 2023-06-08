from __future__ import annotations

import unittest

import cohdl
from cohdl import std, Bit, Port

from cohdl_testutil import cocotb_util


async def invalid_coroutine(sig):
    raise AssertionError("this is an invalid operation, that cannot be synthesized")


# test that varargs and kwargs work for coroutines
async def wait_for_any(*args, **kwargs):
    return await any([*args, *kwargs.values()])


class test_await_fn_03(cohdl.Entity):
    clk = Port.input(Bit)

    a = Port.input(Bit)
    b = Port.input(Bit)
    c = Port.input(Bit)
    d = Port.input(Bit)

    output = Port.output(Bit)

    def architecture(self):
        clk = std.Clock(self.clk)

        @std.sequential(clk)
        async def proc_simple():
            # invalid coroutine is not converted
            # when it is not awaited
            invalid_coroutine(self.a)
            await wait_for_any(self.a, self.b, xyz=self.c, asdf=self.d)
            self.output <<= self.a


#
# test code
#


@cocotb_util.test()
async def testbench_await_fn_03(dut: test_await_fn_03):
    seq = cocotb_util.SequentialTest(dut.clk)

    async def test(a, b, c, d, expected):
        cocotb_util.assign(dut.a, a)
        cocotb_util.assign(dut.b, b)
        cocotb_util.assign(dut.c, c)
        cocotb_util.assign(dut.d, d)
        await seq.tick()
        await seq.tick()
        assert dut.output == expected

    await test(1, 0, 0, 0, 1)
    await test(0, 0, 1, 0, 0)
    await test(1, 0, 0, 1, 1)
    await test(0, 0, 0, 0, 1)


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_await_fn_03, __file__, self.__module__)
