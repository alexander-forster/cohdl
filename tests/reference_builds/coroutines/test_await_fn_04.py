from __future__ import annotations

import unittest

import cohdl
from cohdl import std, Bit, BitVector, Port, true

from cohdl_testutil import cocotb_util


class test_await_fn_04(cohdl.Entity):
    clk = Port.input(Bit)
    addr = Port.input(BitVector[2])
    input = Port.input(Bit)
    result = Port.output(Bit, default=False)
    toggle = Port.output(Bit, default=False)

    def architecture(self):
        async def minimal_impl():
            if self.addr == "01":
                self.result <<= self.input
            elif self.addr == "10":
                await true

        @std.sequential(std.Clock(self.clk))
        async def minimal():
            await minimal_impl()
            self.toggle <<= ~self.toggle
            await true


#
# test code
#


@cocotb_util.test()
async def testbench_await_fn_04(dut: test_await_fn_04):
    seq = cocotb_util.SequentialTest(dut.clk)

    addr_gen = cocotb_util.ConstrainedGenerator(2)
    input_gen = cocotb_util.ConstrainedGenerator(1)

    result = 0
    addr = addr_gen.random()
    input = input_gen.random()
    toggle = False

    await seq.tick()

    def update():
        nonlocal result, toggle

        while True:
            if addr.as_int() == 1:
                result = input.as_int()
            elif addr.as_int() == 2:
                yield
            toggle = not toggle
            yield
            yield

    u = update()

    for _ in range(512):
        cocotb_util.assign(dut.addr, addr)
        cocotb_util.assign(dut.input, input)
        await seq.tick()
        u.send(None)

        print(addr, input, result, dut.result.value)

        assert dut.result.value == result
        assert dut.toggle.value == toggle

        addr = addr_gen.random()
        input = input_gen.random()


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_await_fn_04, __file__, self.__module__)
