from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, Port, Unsigned, Variable, Null, true, false
from cohdl import std

from cohdl_testutil import cocotb_util
from cohdl_testutil.cocotb_mock import MockBase


class test_while_break_01(cohdl.Entity):
    clk = Port.input(Bit)
    reset = Port.input(Bit)
    state = Port.output(Unsigned[3], default=Null)
    step = Port.input(Bit)

    do_continue = Port.input(Bit)

    def architecture(self):
        cnt = Variable[Unsigned[3]](7)

        @std.sequential(std.Clock(self.clk), std.Reset(self.reset))
        async def proc():
            nonlocal cnt

            while True:
                cnt @= cnt - 1
                self.state <<= cnt
                await self.step
                break

            self.state <<= 5


#
# test code
#


class Mock(MockBase):
    def __init__(self, dut: test_while_break_01, *, record=False, no_assert=False):
        super().__init__(dut.clk, record=record, no_assert=no_assert)
        cv = cocotb_util.ConstraindValue
        self.reset = self.inpair(dut.reset, cv(1), "reset")
        self.state = self.outpair(dut.state, cv(3, default=0), "state")
        self.step = self.inpair(dut.step, cv(1), "step")
        self._reset_cond = lambda: self.reset
        self.cnt = 7

    def _reset(self):
        self.cnt = 7
        super()._reset()

    def mock(self):
        while True:
            self.cnt = (self.cnt + 8 - 1) % 8
            self.state <<= self.cnt
            yield from self.await_cond(lambda: self.step)
            break
        self.state <<= 5


@cocotb_util.test()
async def testbench_while_break_01(dut: test_while_break_01):
    mock = Mock(dut)
    mock.zero_inputs()
    mock.check()

    for _ in range(100):
        mock.reset.assign_maybe(True, 0.1)
        mock.step.randomize()
        await mock.next_step()
        mock.reset <<= False


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_while_break_01, __file__, self.__module__)
