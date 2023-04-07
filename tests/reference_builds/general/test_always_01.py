from __future__ import annotations


import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Signal, Unsigned, Signed, always
from cohdl import std

import itertools
from cohdl_testutil import cocotb_util
from cohdl_testutil.cocotb_mock import MockBase


class test_always_01(cohdl.Entity):
    clk = Port.input(Bit)

    enable = Port.input(Bit)

    inp1 = Port.input(BitVector[4])
    inp2 = Port.input(BitVector[4])

    output = Port.output(BitVector[4])

    def architecture(self):
        @std.sequential(std.Clock(self.clk))
        async def proc():
            always_sig = always(self.inp1 | self.inp2)
            await self.enable
            self.output <<= always_sig


#
# test code
#


class Mock(MockBase):
    def __init__(self, dut: test_always_01, *, record=False, no_assert=False):
        super().__init__(dut.clk, record=record, no_assert=no_assert)

        cv = cocotb_util.ConstraindValue
        self.enable = self.inpair(dut.enable, cv(1), "enable")
        self.inp1 = self.inpair(dut.inp1, cv(4), "inp1")
        self.inp2 = self.inpair(dut.inp2, cv(4), "inp2")
        self.output = self.outpair(dut.output, cv(4), "output")

        self.always_sig = self.inp1 | self.inp2

    def concurrent(self):
        self.always_sig = self.inp1 | self.inp2

    def mock(self):
        if self.enable:
            self.output <<= self.always_sig

        # needed to turn function into a generator
        if False:
            yield


@cocotb_util.test()
async def testbench_always_01(dut: test_always_01):
    mock = Mock(dut)
    mock.zero_inputs()
    mock.check()

    for _ in range(32):
        await mock.next_step()
        mock.enable.randomize()
        mock.inp1.randomize()
        mock.inp2.randomize()


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_always_01, __file__, self.__module__)
