from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Signal, Unsigned, Signed, Null
from cohdl import std

from cohdl_testutil import cocotb_util
from cohdl_testutil.cocotb_mock import MockBase


class test_await_03(cohdl.Entity):
    clk = Port.input(Bit)
    step = Port.input(Bit)

    inp1 = Port.input(Bit)
    inp2 = Port.input(BitVector[4])
    inp3 = Port.input(Unsigned[4])

    out1 = Port.output(Bit, default=Null)
    out2 = Port.output(BitVector[4], default=Null)
    out3 = Port.output(Unsigned[4], default=Null)

    outimm1 = Port.output(Bit, default=Null)
    outimm2 = Port.output(BitVector[4], default=Null)
    outimm3 = Port.output(Unsigned[4], default=Null)

    def architecture(self):
        @std.sequential(std.Clock(self.clk))
        async def proc():
            await self.step

            a = Signal[Bit](self.inp1)
            self.outimm1 <<= a

            await self.step

            b = Signal[BitVector[4]](self.inp2)
            self.outimm2 <<= b

            await self.step
            self.out1 <<= a
            self.out2 <<= b
            self.out3 <<= self.inp3
            self.outimm3 <<= self.inp3


#
# test code
#


class Mock(MockBase):
    def __init__(self, dut: test_await_03, *, record=False, no_assert=False):
        super().__init__(dut.clk, record=record, no_assert=no_assert)

        cv = cocotb_util.ConstraindValue

        self.step = self.inpair(dut.step, cv(1), "step")
        self.inp1 = self.inpair(dut.inp1, cv(1), "inp1")
        self.inp2 = self.inpair(dut.inp2, cv(4), "inp2")
        self.inp3 = self.inpair(dut.inp3, cv(4), "inp3")
        self.out1 = self.outpair(dut.out1, cv(1), "out1")
        self.out2 = self.outpair(dut.out2, cv(4), "out2")
        self.out3 = self.outpair(dut.out3, cv(4), "out3")
        self.outimm1 = self.outpair(dut.outimm1, cv(1), "outimm1")
        self.outimm2 = self.outpair(dut.outimm2, cv(4), "outimm2")
        self.outimm3 = self.outpair(dut.outimm3, cv(4), "outimm3")

    def mock(self):
        if not self.step:
            yield from self.await_cond(lambda: self.step)

        a = self.inp1.get()
        self.outimm1 <<= a

        yield from self.await_cond(lambda: self.step)

        b = self.inp2.get()
        self.outimm2 <<= b

        yield from self.await_cond(lambda: self.step)

        self.out1 <<= a
        self.out2 <<= b
        self.out3 <<= self.inp3.get()
        self.outimm3 <<= self.inp3.get()


@cocotb_util.test()
async def testbench_local_declaration_03(dut: test_await_03):
    mock = Mock(dut)
    mock.step <<= 0
    mock.check()

    for _ in range(32):
        await mock.next_step()
        mock.step <<= 1
        mock.inp1.randomize()
        mock.inp2.randomize()
        mock.inp3.randomize()


class Unittest(unittest.TestCase):
    def test_await_03(self):
        cocotb_util.run_cocotb_tests(test_await_03, __file__, self.__module__)
