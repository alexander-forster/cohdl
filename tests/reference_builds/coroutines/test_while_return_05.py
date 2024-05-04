from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, Port, Unsigned, Variable, Null
from cohdl import std

from cohdl_testutil import cocotb_util
from cohdl_testutil.cocotb_mock import MockBase


class CondWithSideEffect:
    def __init__(self, cond, target, value):
        self.cond = cond
        self.target = target
        self.value = value

    def __bool__(self):
        self.target <<= self.value
        return bool(self.cond)


class test_while_return_05(cohdl.Entity):
    clk = Port.input(Bit)
    reset = Port.input(Bit)
    state = Port.output(Unsigned[4], default=Null)
    cnt_return = Port.output(Unsigned[4], default=Null)

    do_return = Port.input(Unsigned[2])

    def architecture(self):
        async def coro(cnt):
            while cnt:
                cnt @= cnt - 1
                self.state <<= cnt

                if self.do_return == 0:
                    self.cnt_return <<= self.cnt_return + 1
                    return
                elif self.do_return == 1:
                    while CondWithSideEffect(
                        False, self.cnt_return, self.cnt_return + 4
                    ):
                        pass

                    continue
                elif self.do_return == 2:
                    self.cnt_return <<= self.cnt_return + 2
                    return
                else:
                    while CondWithSideEffect(
                        False, self.cnt_return, self.cnt_return + 3
                    ):
                        try:
                            raise AssertionError("this line should not be evaluated")
                        except:
                            raise
                    break

        @std.sequential(std.Clock(self.clk), std.Reset(self.reset))
        async def proc():
            cnt = Variable[Unsigned[4]](8)
            await coro(cnt)


#
# test code
#


class Mock(MockBase):
    def __init__(self, dut: test_while_return_05, *, record=False, no_assert=False):
        super().__init__(dut.clk, record=record, no_assert=no_assert)
        cv = cocotb_util.ConstraindValue
        self.reset = self.inpair(dut.reset, cv(1), "reset")
        self.do_return = self.inpair(dut.do_return, cv(2, default=0), "do_return")
        self.state = self.outpair(dut.state, cv(4, default=0), "state")
        self.cnt_return = self.outpair(dut.cnt_return, cv(4, default=0), "cnt_return")
        self._reset_cond = lambda: self.reset

    def mock(self):
        cnt = 8
        yield
        while cnt:
            cnt -= 1
            self.state <<= cnt

            if self.do_return.get() == 0:
                self.cnt_return <<= (self.cnt_return.get() + 1) % 16
                break
            elif self.do_return.get() == 1:
                self.cnt_return <<= (self.cnt_return.get() + 4) % 16
                yield
            elif self.do_return.get() == 2:
                self.cnt_return <<= (self.cnt_return.get() + 2) % 16
                break
            else:
                self.cnt_return <<= (self.cnt_return.get() + 3) % 16
                yield
                break


@cocotb_util.test()
async def testbench_while_return_05(dut: test_while_return_05):
    mock = Mock(dut)
    mock.zero_inputs()
    mock.check()

    for _ in range(1000):
        mock.reset.assign_maybe(True, 0.1)
        mock.do_return.randomize()
        await mock.next_step()
        mock.reset <<= False


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_while_return_05, __file__, self.__module__)
