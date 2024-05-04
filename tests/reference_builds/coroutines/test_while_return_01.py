from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, Port, Unsigned, Variable, Null, true, false
from cohdl import std

from cohdl_testutil import cocotb_util
from cohdl_testutil.cocotb_mock import MockBase


class test_while_return_01(cohdl.Entity):
    clk = Port.input(Bit)
    reset = Port.input(Bit)
    state = Port.output(Unsigned[4], default=Null)
    cnt_return = Port.output(Unsigned[4], default=Null)

    do_return = Port.input(Bit)

    def architecture(self):
        async def coro(cnt):
            while cnt:
                cnt @= cnt - 1
                self.state <<= cnt

                if self.do_return:
                    self.cnt_return <<= self.cnt_return + 1
                    return

        @std.sequential(std.Clock(self.clk), std.Reset(self.reset))
        async def proc():
            cnt = Variable[Unsigned[4]](8)
            await coro(cnt)


#
# test code
#


class Mock(MockBase):
    def __init__(self, dut: test_while_return_01, *, record=False, no_assert=False):
        super().__init__(dut.clk, record=record, no_assert=no_assert)
        cv = cocotb_util.ConstraindValue
        self.reset = self.inpair(dut.reset, cv(1), "reset")
        self.do_return = self.inpair(dut.do_return, cv(1, default=0), "do_return")
        self.state = self.outpair(dut.state, cv(4, default=0), "state")
        self.cnt_return = self.outpair(dut.cnt_return, cv(4, default=0), "cnt_return")
        self._reset_cond = lambda: self.reset

    def mock(self):
        cnt = 8
        yield
        while cnt:
            cnt -= 1
            self.state <<= cnt

            if self.do_return:
                self.cnt_return <<= (self.cnt_return.get() + 1) % 16
                break
            else:
                yield


@cocotb_util.test()
async def testbench_while_return_01(dut: test_while_return_01):
    mock = Mock(dut)
    mock.zero_inputs()
    mock.check()

    for _ in range(64):
        mock.reset.assign_maybe(True, 0.1)
        mock.do_return.assign_maybe(True, 0.3)
        await mock.next_step()
        mock.reset <<= False
        mock.do_return <<= False


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_while_return_01, __file__, self.__module__)
