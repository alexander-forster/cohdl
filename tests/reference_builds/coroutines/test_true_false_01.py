from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Signal, Unsigned, Signed, Null, true, false
from cohdl import std

from cohdl_testutil import cocotb_util
from cohdl_testutil.cocotb_mock import MockBase


class test_true_false_01(cohdl.Entity):
    clk = Port.input(Bit)
    state = Port.output(Unsigned[3], default=Null)

    def architecture(self):
        @std.sequential(std.Clock(self.clk))
        async def proc():
            self.state <<= 1
            await true
            self.state <<= 2
            await true
            self.state <<= 3
            await true
            self.state <<= 4
            await false


#
# test code
#


class Mock(MockBase):
    def __init__(self, dut: test_true_false_01, *, record=False, no_assert=False):
        super().__init__(dut.clk, record=record, no_assert=no_assert)

        cv = cocotb_util.ConstraindValue
        self.state = self.outpair(dut.state, cv(3), "state")

    def mock(self):
        self.state <<= 1
        yield
        self.state <<= 2
        yield
        self.state <<= 3
        yield
        self.state <<= 4
        while True:
            yield


@cocotb_util.test()
async def testbench_true_false_01(dut: test_true_false_01):
    mock = Mock(dut)
    mock.zero_inputs()
    mock.check()

    for _ in range(8):
        await mock.next_step()


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_true_false_01, __file__, self.__module__)
