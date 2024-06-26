from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, Port, Unsigned, Variable, Null, true, false
from cohdl import std

from cohdl_testutil import cocotb_util
from cohdl_testutil.cocotb_mock import MockBase


class test_while_break_continue_02(cohdl.Entity):
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

            self.state <<= cnt + 1

            while True:
                cnt @= cnt - 1
                self.state <<= cnt
                await self.step

                if self.do_continue:
                    continue
                else:
                    break

            self.state <<= 7
            await self.step


#
# test code
#


class Mock(MockBase):
    def __init__(
        self, dut: test_while_break_continue_02, *, record=False, no_assert=False
    ):
        super().__init__(dut.clk, record=record, no_assert=no_assert)
        cv = cocotb_util.ConstraindValue
        self.reset = self.inpair(dut.reset, cv(1), "reset")
        self.state = self.outpair(dut.state, cv(3, default=0), "state")
        self.step = self.inpair(dut.step, cv(1), "step")
        self.do_continue = self.inpair(dut.do_continue, cv(1), "do_continue")
        self._reset_cond = lambda: self.reset
        self.cnt = 7

    def _reset(self):
        self.cnt = 7
        super()._reset()

    def mock(self):
        self.state <<= (self.cnt + 1) % 8
        yield
        while True:
            self.cnt = (self.cnt + 8 - 1) % 8
            self.state <<= self.cnt
            yield from self.await_cond(lambda: self.step)

            if self.do_continue:
                continue
            else:
                self.state <<= 7
                yield from self.await_cond(lambda: self.step)
                break


@cocotb_util.test()
async def testbench_while_break_continue_02(dut: test_while_break_continue_02):
    mock = Mock(dut)
    mock.zero_inputs()
    mock.check()

    for _ in range(100):
        mock.reset.assign_maybe(True, 0.1)
        mock.step.randomize()
        mock.do_continue.randomize()
        await mock.next_step()
        mock.reset <<= False

    mock.dump_record()


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(
            test_while_break_continue_02, __file__, self.__module__
        )
