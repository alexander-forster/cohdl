from __future__ import annotations

import unittest

import cohdl
from cohdl import std, Bit, BitVector, Port

from cohdl_testutil import cocotb_util


class test_shift_out(cohdl.Entity):
    clk = Port.input(Bit)

    start = Port.input(Bit)

    vec_inp = Port.input(BitVector[8])

    res = Port.output(Bit)
    res_delay = Port.output(Bit)
    res_msb = Port.output(Bit)
    res_msb_delay = Port.output(Bit)

    def architecture(self):
        clk = std.Clock(self.clk)

        @std.sequential(clk)
        async def proc_out():
            await self.start
            reg = std.OutShiftRegister(self.vec_inp)
            await reg.shift_all(self.res)

        @std.sequential(clk)
        async def proc_out():
            await self.start
            reg = std.OutShiftRegister(self.vec_inp)
            await reg.shift_all(self.res_delay, shift_delayed=True)

            await self.start
            reg.set_data(self.vec_inp)

            while not reg.empty():
                self.res_delay <<= reg.shift()

        @std.sequential(clk)
        async def proc_out():
            await self.start
            reg = std.OutShiftRegister(self.vec_inp, msb_first=True)
            await reg.shift_all(self.res_msb)

        @std.sequential(clk)
        async def proc_out():
            await self.start
            reg = std.OutShiftRegister(self.vec_inp, msb_first=True)
            await reg.shift_all(self.res_msb_delay, shift_delayed=True)

            await self.start
            reg.set_data(self.vec_inp)

            while not reg.empty():
                self.res_msb_delay <<= reg.shift()


#
# test code
#


@cocotb_util.test()
async def testbench_shift(dut: test_shift_out):
    gen = cocotb_util.ConstrainedGenerator(8)

    async def wait_for(n):
        for _ in range(n):
            await seq.tick()

    seq = cocotb_util.SequentialTest(dut.clk)
    dut.start.value = 0

    for _ in range(16):
        val = gen.random()
        await wait_for(5)
        dut.start.value = 1
        dut.vec_inp.value = val.as_int()

        def in_range(x):
            return 0 <= x <= 7

        for i in range(9):
            res = i
            res_delay = i - 1
            res_msb = 7 - i
            res_msb_delay = 8 - i

            await wait_for(1)

            if in_range(res):
                assert dut.res.value == val[res].as_int()

            if in_range(res_delay):
                assert dut.res_delay.value == val[res_delay].as_int()

            if in_range(res_msb):
                assert dut.res_msb.value == val[res_msb].as_int()

            if in_range(res_msb_delay):
                assert dut.res_msb_delay.value == val[res_msb_delay].as_int()

            dut.start.value = 0

        await wait_for(20)


class Unittest(unittest.TestCase):
    def test_shift(self):
        cocotb_util.run_cocotb_tests(test_shift_out, __file__, self.__module__)
