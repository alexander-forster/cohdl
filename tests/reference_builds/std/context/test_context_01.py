from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Signal, Unsigned
from cohdl import std

from cohdl_testutil import cocotb_util
from cohdl_testutil.cocotb_mock import MockBase
import os

reset_active_low = eval(os.getenv("cohdl_test_reset_active_low", "None"))
reset_async = eval(os.getenv("cohdl_test_reset_async", "None"))
use_step_cond = eval(os.getenv("cohdl_test_use_step_cond", "None"))


def gen_entity():
    class test_context_01(cohdl.Entity):
        clk = Port.input(Bit)
        reset = Port.input(Bit)
        step = Port.input(Bit)

        out_bit = Port.output(Bit)
        out_bitvector = Port.output(BitVector[3])

        resetable_bit = Port.output(Bit, default=False)
        resetable_bitvector = Port.output(BitVector[3], default="000")

        def architecture(self):
            ctx = std.SequentialContext(
                std.Clock(self.clk),
                std.Reset(
                    self.reset, active_low=reset_active_low, is_async=reset_async
                ),
                step_cond=(lambda: self.step) if use_step_cond else None,
            )

            cnt = Signal[Unsigned[3]](3)

            if use_step_cond:
                step = cohdl.true
            else:
                step = self.step

            @ctx
            async def proc():
                cnt.next = cnt + 1
                await step
                self.out_bit <<= cnt[1]
                self.resetable_bit <<= cnt[1]
                cnt.next = cnt + 1
                await step
                self.out_bitvector <<= cnt
                self.resetable_bitvector <<= cnt

    return test_context_01


#
# test code
#


class Mock(MockBase):
    def __init__(self, dut, *, record=False, no_assert=False):
        super().__init__(dut.clk, record=record, no_assert=no_assert)

        cv = cocotb_util.ConstraindValue

        self.step = self.inpair(dut.step, cv(1), "step")
        self.reset = self.inpair(dut.reset, cv(1), "reset")

        self.out_bit = self.inpair(dut.out_bit, cv(1), "out_bit")
        self.out_bitvector = self.inpair(dut.out_bitvector, cv(3), "out_bitvector")
        self.resetable_bit = self.outpair(dut.resetable_bit, cv(1), "resetable_bit")
        self.resetable_bitvector = self.outpair(
            dut.resetable_bitvector, cv(3), "resetable_bitvector"
        )

        self.cnt = 3

        if reset_active_low is True:
            self._reset_cond = lambda: not self.reset
        elif reset_active_low is False:
            self._reset_cond = lambda: self.reset
        else:
            raise AssertionError("invalid environment parameter")

        if reset_async is True:
            self._reset_async = True
        elif reset_async is False:
            self._reset_async = False
        else:
            raise AssertionError("invalid environment parameter")

    def _reset(self):
        self.resetable_bit <<= 0
        self.resetable_bitvector <<= 0
        self.cnt = 3

    def concurrent(self):
        if self._reset_async and self._reset_cond():
            self.reset_sim()

    def mock(self):
        if use_step_cond:
            if not self.step:
                yield from self.await_cond(lambda: self.step)

        self.cnt = (self.cnt + 1) % 8

        yield from self.await_cond(lambda: self.step)

        self.out_bit <<= (self.cnt >> 1) & 1
        self.resetable_bit <<= (self.cnt >> 1) & 1
        self.cnt = (self.cnt + 1) % 8

        yield from self.await_cond(lambda: self.step)

        self.out_bitvector <<= self.cnt
        self.resetable_bitvector <<= self.cnt


@cocotb_util.test()
async def testbench_context_01(dut):
    mock = Mock(dut)
    mock.step <<= 0
    mock.check()

    assert reset_active_low in (True, False)

    reset_state = reset_active_low is False

    for _ in range(128):
        mock.reset.assign_maybe(reset_state, 0.2)
        await mock.next_step()
        mock.step.randomize()
        mock.reset.assign(not reset_state)
        await mock.delta_step()
        mock.reset.assign_maybe(reset_state, 0.2)
        await mock.delta_step()
        mock.reset.assign(not reset_state)


class Unittest(unittest.TestCase):
    def test_all(self):
        for active_low in (True, False):
            for is_async in (True, False):
                for step_cond in (True, False):
                    global reset_active_low, reset_async, use_step_cond
                    reset_active_low = active_low
                    reset_async = is_async
                    use_step_cond = step_cond
                    cocotb_util.run_cocotb_tests(
                        gen_entity(),
                        __file__,
                        self.__module__,
                        extra_env={
                            "cohdl_test_reset_active_low": str(active_low),
                            "cohdl_test_reset_async": str(is_async),
                            "cohdl_test_use_step_cond": str(use_step_cond),
                        },
                    )
