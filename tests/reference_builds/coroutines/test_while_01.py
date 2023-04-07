from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, Port, Unsigned, Variable, Null, true, false
from cohdl import std

from cohdl_testutil import cocotb_util
from cohdl_testutil.cocotb_mock import MockBase


class test_while_01(cohdl.Entity):
    clk = Port.input(Bit)
    reset = Port.input(Bit)
    state = Port.output(Unsigned[4], default=Null)

    def architecture(self):
        @std.sequential(std.Clock(self.clk), std.Reset(self.reset))
        async def proc():
            cnt = Variable[Unsigned[4]](8)

            while cnt:
                cnt @= cnt - 1
                self.state <<= cnt


#
# test code
#


class Mock(MockBase):
    def __init__(self, dut: test_while_01, *, record=False, no_assert=False):
        super().__init__(dut.clk, record=record, no_assert=no_assert)
        cv = cocotb_util.ConstraindValue
        self.reset = self.inpair(dut.reset, cv(1), "reset")
        self.state = self.outpair(dut.state, cv(4, default=0), "state")
        self._reset_cond = lambda: self.reset

    def mock(self):
        cnt = 8
        yield
        while cnt:
            cnt -= 1
            self.state <<= cnt
            yield


@cocotb_util.test()
async def testbench_while_01(dut: test_while_01):
    mock = Mock(dut)
    mock.zero_inputs()
    mock.check()

    for _ in range(32):
        mock.reset.assign_maybe(True, 0.2)
        await mock.next_step()
        mock.reset <<= False


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_while_01, __file__, self.__module__)
