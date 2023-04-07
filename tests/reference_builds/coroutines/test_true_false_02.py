from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Signal, Unsigned, Signed, Null, true, false
from cohdl import std

from cohdl_testutil import cocotb_util
from cohdl_testutil.cocotb_mock import MockBase


class test_true_false_02(cohdl.Entity):
    clk = Port.input(Bit)
    state = Port.output(Unsigned[3], default=Null)
    inp_1 = Port.input(Bit)

    def architecture(self):
        @std.sequential(std.Clock(self.clk))
        async def proc():
            await true
            self.state <<= 1
            await true
            self.state <<= 2
            await self.inp_1
            self.state <<= 3
            await true
            self.state <<= 4


#
# test code
#


class Mock(MockBase):
    def __init__(self, dut: test_true_false_02, *, record=False, no_assert=False):
        super().__init__(dut.clk, record=record, no_assert=no_assert)

        cv = cocotb_util.ConstraindValue
        self.state = self.outpair(dut.state, cv(3), "state")
        self.inp_1 = self.inpair(dut.inp_1, cv(1), "inp_1")

    def mock(self):
        self.state <<= 1
        yield
        self.state <<= 2
        yield from self.await_cond(lambda: self.inp_1)
        self.state <<= 3
        yield
        self.state <<= 4


@cocotb_util.test()
async def testbench_true_false_02(dut: test_true_false_02):
    mock = Mock(dut)
    mock.zero_inputs()
    mock.check()

    for _ in range(16):
        await mock.next_step()
        mock.inp_1.randomize()


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_true_false_02, __file__, self.__module__)
