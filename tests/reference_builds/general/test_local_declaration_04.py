from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Signal, Unsigned, Signed
from cohdl import std

from cohdl_testutil import cocotb_util
from cohdl_testutil.cocotb_mock import MockBase


class test_local_declaration_04(cohdl.Entity):
    clk = Port.input(Bit)
    step = Port.input(Bit)

    inp1 = Port.input(Bit)
    inp2 = Port.input(BitVector[4])
    inp3 = Port.input(Unsigned[4])
    inp4 = Port.input(Signed[4])

    out1 = Port.output(Bit)
    out2 = Port.output(BitVector[4])
    out3 = Port.output(Unsigned[4])
    out4 = Port.output(Signed[4])

    def architecture(self):
        @std.sequential(std.Clock(self.clk))
        async def proc():
            await self.step

            a = Signal[Bit](self.inp1)
            b = Signal[BitVector[4]](self.inp2)
            c = Signal[Unsigned[4]](self.inp3)
            d = Signal[Signed[4]](self.inp4)

            self.out1 <<= a
            self.out2 <<= b
            self.out3 <<= c
            self.out4 <<= d


#
# test code
#


class Mock(MockBase):
    def __init__(self, dut: test_local_declaration_04):
        super().__init__(dut.clk, record=True)

        cv = cocotb_util.ConstraindValue

        self.step = self.inpair(dut.step, cv(1), "step")
        self.inp1 = self.inpair(dut.inp1, cv(1), "inp1")
        self.inp2 = self.inpair(dut.inp2, cv(4), "inp2")
        self.inp3 = self.inpair(dut.inp3, cv(4), "inp3")
        self.inp4 = self.inpair(dut.inp4, cv(4), "inp4")
        self.out1 = self.outpair(dut.out1, cv(1), "out1")
        self.out2 = self.outpair(dut.out2, cv(4), "out2")
        self.out3 = self.outpair(dut.out3, cv(4), "out3")
        self.out4 = self.outpair(dut.out4, cv(4), "out4")

    def mock(self):
        if not self.step:
            yield from self.await_cond(lambda: self.step)
        self.out1 <<= self.inp1
        self.out2 <<= self.inp2
        self.out3 <<= self.inp3
        self.out4 <<= self.inp4


@cocotb_util.test()
async def testbench_local_declaration_04(dut: test_local_declaration_04):
    mock = Mock(dut)
    mock.step <<= 1

    for _ in range(64):
        await mock.next_step()
        mock.inp1.randomize()
        mock.inp2.randomize()
        mock.inp3.randomize()
        mock.inp4.randomize()


class Unittest(unittest.TestCase):
    def test_local_declaration_04(self):
        cocotb_util.run_cocotb_tests(
            test_local_declaration_04, __file__, self.__module__
        )
