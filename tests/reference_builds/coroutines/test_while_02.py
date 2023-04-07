from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, Port, Unsigned, Variable, Null, true, false
from cohdl import std

from cohdl_testutil import cocotb_util
from cohdl_testutil.cocotb_mock import MockBase


class test_while_02(cohdl.Entity):
    clk = Port.input(Bit)
    reset = Port.input(Bit)
    state = Port.output(Unsigned[4], default=Null)

    select1 = Port.input(Bit)
    select2 = Port.input(Bit)

    def architecture(self):
        @std.sequential(std.Clock(self.clk), std.Reset(self.reset))
        async def proc():
            cnt = Variable[Unsigned[4]](8)

            if self.select1:
                while cnt:
                    cnt @= cnt - 1
                    self.state <<= cnt
            elif self.select2:
                while cnt:
                    cnt @= cnt - 2
                    self.state <<= cnt


#
# test code
#


class Mock(MockBase):
    def __init__(self, dut: test_while_02, *, record=False, no_assert=False):
        super().__init__(dut.clk, record=record, no_assert=no_assert)
        cv = cocotb_util.ConstraindValue
        self.reset = self.inpair(dut.reset, cv(1), "reset")
        self.select1 = self.inpair(dut.select1, cv(1), "select1")
        self.select2 = self.inpair(dut.select2, cv(1), "select2")
        self.state = self.outpair(dut.state, cv(4, default=0), "state")
        self._reset_cond = lambda: self.reset

    def mock(self):
        cnt = 8
        if self.select1:
            yield
            while cnt:
                cnt -= 1
                self.state <<= cnt
                yield
        elif self.select2:
            yield
            while cnt:
                cnt -= 2
                self.state <<= cnt
                yield


@cocotb_util.test()
async def testbench_while_02(dut: test_while_02):
    mock = Mock(dut)
    mock.zero_inputs()
    mock.check()

    for _ in range(64):
        mock.reset.assign_maybe(True, 0.2)
        mock.select1.randomize()
        mock.select2.randomize()
        await mock.next_step()
        mock.reset <<= False


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_while_02, __file__, self.__module__)
