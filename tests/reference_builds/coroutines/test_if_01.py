from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Signal, Unsigned, Signed, Null
from cohdl import std

from cohdl_testutil import cocotb_util
from cohdl_testutil.cocotb_mock import MockBase


class test_if_01(cohdl.Entity):
    clk = Port.input(Bit)
    step = Port.input(Bit)

    inp1 = Port.input(Bit)
    inp2 = Port.input(BitVector[4])
    inp3 = Port.input(Unsigned[4])

    out1 = Port.output(Bit, default=Null)
    out2 = Port.output(BitVector[4], default=Null)
    out3 = Port.output(Unsigned[4], default=Null)

    state = Port.output(Unsigned[3], default=Null)

    def architecture(self):
        @std.sequential(std.Clock(self.clk))
        async def proc():
            self.state <<= 1
            await self.step
            self.out1 <<= self.inp1
            self.state <<= 2
            await self.step

            if self.inp1:
                self.out2 <<= self.inp2
            else:
                self.out2 <<= "0000"

            self.state <<= 3
            await self.step
            self.out3 <<= self.inp3
            self.state <<= 4


#
# test code
#


class Mock(MockBase):
    def __init__(self, dut: test_if_01, *, record=False, no_assert=False):
        super().__init__(dut.clk, record=record, no_assert=no_assert)

        cv = cocotb_util.ConstraindValue

        self.state = self.outpair(dut.state, cv(3), "state")
        self.step = self.inpair(dut.step, cv(1), "step")
        self.inp1 = self.inpair(dut.inp1, cv(1), "inp1")
        self.inp2 = self.inpair(dut.inp2, cv(4), "inp2")
        self.inp3 = self.inpair(dut.inp3, cv(4), "inp3")
        self.out1 = self.outpair(dut.out1, cv(1), "out1")
        self.out2 = self.outpair(dut.out2, cv(4), "out2")
        self.out3 = self.outpair(dut.out3, cv(4), "out3")

    def mock(self):
        self.state <<= 1
        yield from self.await_cond(lambda: self.step)
        self.out1 <<= self.inp1
        self.state <<= 2
        yield from self.await_cond(lambda: self.step)

        if self.inp1.get():
            self.out2 <<= self.inp2
        else:
            self.out2 <<= 0

        self.state <<= 3
        yield from self.await_cond(lambda: self.step)
        self.state <<= 4
        self.out3 <<= self.inp3.get()


@cocotb_util.test()
async def testbench_if_01(dut: test_if_01):
    mock = Mock(dut)
    mock.zero_inputs()
    mock.step <<= 0
    mock.check()

    for _ in range(32):
        await mock.next_step()
        mock.step <<= 1
        mock.inp1.randomize()
        mock.inp2.randomize()
        mock.inp3.randomize()


class Unittest(unittest.TestCase):
    def test_if_01(self):
        cocotb_util.run_cocotb_tests(test_if_01, __file__, self.__module__)
