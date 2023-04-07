from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, Port, Unsigned, Null, true, false
from cohdl import std

from cohdl_testutil import cocotb_util
from cohdl_testutil.cocotb_mock import MockBase


class test_true_false_04(cohdl.Entity):
    clk = Port.input(Bit)
    reset = Port.input(Bit)

    state = Port.output(Unsigned[3], default=Null)
    inp_1 = Port.input(Bit)

    def architecture(self):
        @std.sequential(std.Clock(self.clk), std.Reset(self.reset))
        async def proc():
            await true
            self.state <<= 1
            await true
            self.state <<= 2

            if self.inp_1:
                await false

            self.state <<= 3
            await true
            self.state <<= 4


#
# test code
#


class Mock(MockBase):
    def __init__(self, dut: test_true_false_04, *, record=False, no_assert=False):
        super().__init__(dut.clk, record=record, no_assert=no_assert)
        cv = cocotb_util.ConstraindValue
        self.state = self.outpair(dut.state, cv(3, default=0), "state")
        self.inp_1 = self.inpair(dut.inp_1, cv(1), "inp_1")
        self.reset = self.inpair(dut.reset, cv(1), "reset")
        self._reset_cond = lambda: self.reset

    def mock(self):
        self.state <<= 1
        yield
        self.state <<= 2

        if self.inp_1:
            while True:
                yield

        self.state <<= 3
        yield
        self.state <<= 4


@cocotb_util.test()
async def testbench_true_false_04(dut: test_true_false_04):
    mock = Mock(dut)
    mock.zero_inputs()
    mock.check()

    for _ in range(32):
        await mock.next_step()
        mock.inp_1.randomize()
        mock.reset.randomize()


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_true_false_04, __file__, self.__module__)
