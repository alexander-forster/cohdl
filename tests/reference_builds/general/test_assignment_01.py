from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Signal, Variable, Unsigned, Signed, Null
from cohdl import std

from cohdl_testutil import cocotb_util
from cohdl_testutil.cocotb_mock import MockBase


class test_assignment_01(cohdl.Entity):
    clk = Port.input(Bit)
    step = Port.input(Bit)

    inp1 = Port.input(Bit)
    inp2 = Port.input(BitVector[4])

    out1 = Port.output(Bit, default=Null)
    out2 = Port.output(BitVector[4], default=Null)

    def architecture(self):
        @std.sequential(std.Clock(self.clk))
        async def proc(
            var1=Variable[Bit](),
            var2=Variable[BitVector[4]](),
        ):
            await self.step
            self.out1 <<= self.inp1
            await self.step

            var1 @= self.inp1
            var2.value = self.inp2
            self.out2 ^= var2

            await self.step

            self.out1.next = var1
            self.out2.push = var2


#
# test code
#


class Mock(MockBase):
    def __init__(self, dut: test_assignment_01, *, record=False, no_assert=False):
        super().__init__(dut.clk, record=record, no_assert=no_assert)

        cv = cocotb_util.ConstraindValue

        self.step = self.inpair(dut.step, cv(1), "step")
        self.inp1 = self.inpair(dut.inp1, cv(1), "inp1")
        self.inp2 = self.inpair(dut.inp2, cv(4), "inp2")
        self.out1 = self.outpair(dut.out1, cv(1), "out1")
        self.out2 = self.outpair(dut.out2, cv(4), "out2")

    def mock(self):
        self.out2.assign(0)
        if not self.step:
            yield from self.await_cond(lambda: self.step)

        self.out1 <<= self.inp1
        yield from self.await_cond(lambda: self.step)

        var1 = self.inp1.get()
        var2 = self.inp2.get()

        self.out2 <<= var2

        yield from self.await_cond(lambda: (self.out2.assign(0), self.step)[1])

        self.out1 <<= var1
        self.out2 <<= var2


@cocotb_util.test()
async def testbench_local_declaration_03(dut: test_assignment_01):
    mock = Mock(dut)
    mock.step <<= 0
    mock.check()

    for _ in range(32):
        await mock.next_step()
        mock.step.randomize()
        mock.inp1.randomize()
        mock.inp2.randomize()


class Unittest(unittest.TestCase):
    def test_assignment_01(self):
        cocotb_util.run_cocotb_tests(test_assignment_01, __file__, self.__module__)
