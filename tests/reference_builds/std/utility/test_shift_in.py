from __future__ import annotations

import unittest

import cohdl
from cohdl import std, Bit, BitVector, Port

from cohdl_testutil import cocotb_util


class test_shift_in(cohdl.Entity):
    clk = Port.input(Bit)

    start = Port.input(Bit)

    bit_inp = Port.input(Bit)

    res_in = Port.output(BitVector[5])
    res_in_delay = Port.output(BitVector[5])
    res_in_msb = Port.output(BitVector[5])
    res_in_msb_delay = Port.output(BitVector[5])

    def architecture(self):
        clk = std.Clock(self.clk)

        @std.sequential(clk)
        async def proc_in():
            await self.start
            reg = std.InShiftRegister(5)
            self.res_in <<= await reg.shift_all(self.bit_inp)
            reg.clear()
            await self.start
            reg.shift(self.bit_inp)
            while not reg.full():
                reg.shift(self.bit_inp)
            self.res_in <<= reg.data()

        @std.sequential(clk)
        async def proc_in_delay():
            await self.start
            reg = std.InShiftRegister(5)
            self.res_in_delay <<= await reg.shift_all(self.bit_inp, shift_delayed=True)
            reg.clear()
            await self.start
            while not reg.full():
                reg.shift(self.bit_inp)
            self.res_in_delay <<= reg.data()

        @std.sequential(clk)
        async def proc_in_msb():
            await self.start
            reg = std.InShiftRegister(5, msb_first=True)
            self.res_in_msb <<= await reg.shift_all(self.bit_inp)
            reg.clear()
            await self.start
            reg.shift(self.bit_inp)
            while not reg.full():
                reg.shift(self.bit_inp)
            self.res_in_msb <<= reg.data()

        @std.sequential(clk)
        async def proc_in_msb_delay():
            await self.start
            reg = std.InShiftRegister(5, msb_first=True)
            self.res_in_msb_delay <<= await reg.shift_all(
                self.bit_inp, shift_delayed=True
            )
            reg.clear()
            await self.start
            while not reg.full():
                reg.shift(self.bit_inp)
            self.res_in_msb_delay <<= reg.data()


#
# test code
#


@cocotb_util.test()
async def testbench_shift(dut: test_shift_in):
    gen = cocotb_util.ConstrainedGenerator(6)

    async def wait_for(n):
        for _ in range(n):
            await seq.tick()

    seq = cocotb_util.SequentialTest(dut.clk)
    dut.start.value = 0

    for val in gen.all():
        shifted = val.copy()
        await wait_for(5)
        dut.start.value = 1

        for _ in range(7):
            dut.bit_inp.value = shifted[0].as_int()
            shifted = shifted >> 1
            await wait_for(1)
            dut.start.value = 0
        await wait_for(3)

        slice = val.get_slice(0, 4)
        slice_delayed = val.get_slice(1, 5)

        assert dut.res_in.value == slice.as_int()
        assert dut.res_in_delay.value == slice_delayed.as_int()
        assert dut.res_in_msb.value == int(slice.as_str()[::-1], 2)
        assert dut.res_in_msb_delay.value == int(slice_delayed.as_str()[::-1], 2)


class Unittest(unittest.TestCase):
    def test_shift(self):
        cocotb_util.run_cocotb_tests(test_shift_in, __file__, self.__module__)
