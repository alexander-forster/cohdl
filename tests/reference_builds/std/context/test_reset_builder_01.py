import unittest

import cohdl
from cohdl import Bit, Port
from cohdl import std

from cohdl_testutil import cocotb_util


class test_reset_builder_01(cohdl.Entity):
    clk = Port.input(Bit)
    reset = Port.input(Bit)

    cond = Port.input(Bit)

    high_0 = Port.output(Bit, default=False)
    high_or_none = Port.output(Bit, default=False)
    high_and_none = Port.output(Bit, default=False)
    high_or_low = Port.output(Bit, default=False)
    high_and_low = Port.output(Bit, default=False)
    high_or_high = Port.output(Bit, default=False)
    high_and_high = Port.output(Bit, default=False)

    low_0 = Port.output(Bit, default=False)
    low_or_none = Port.output(Bit, default=False)
    low_and_none = Port.output(Bit, default=False)
    low_or_low = Port.output(Bit, default=False)
    low_and_low = Port.output(Bit, default=False)
    low_or_high = Port.output(Bit, default=False)
    low_and_high = Port.output(Bit, default=False)

    def architecture(self):
        ctx_high = std.SequentialContext(std.Clock(self.clk), std.Reset(self.reset))
        ctx_low = std.SequentialContext(
            std.Clock(self.clk), std.Reset(self.reset, active_low=True)
        )

        def gen_proc(
            ctx: std.SequentialContext, out, expected_active_low, expected_async
        ):
            @ctx
            def proc():
                out.next = True

            assert ctx.reset().is_active_low() == expected_active_low
            assert ctx.reset().is_async() == expected_async

        gen_proc(ctx_high, self.high_0, False, False)
        gen_proc(ctx_high.or_reset(self.cond), self.high_or_none, False, False)
        gen_proc(ctx_high.and_reset(self.cond), self.high_and_none, False, False)
        gen_proc(
            ctx_high.or_reset(self.cond, active_low=True), self.high_or_low, True, False
        )
        gen_proc(
            ctx_high.and_reset(self.cond, active_low=True),
            self.high_and_low,
            True,
            False,
        )
        gen_proc(
            ctx_high.or_reset(self.cond, active_low=False),
            self.high_or_high,
            False,
            False,
        )
        gen_proc(
            ctx_high.and_reset(self.cond, active_low=False),
            self.high_and_high,
            False,
            False,
        )

        gen_proc(ctx_low, self.low_0, True, False)
        gen_proc(ctx_low.or_reset(self.cond), self.low_or_none, False, False)
        gen_proc(ctx_low.and_reset(self.cond), self.low_and_none, False, False)
        gen_proc(
            ctx_low.or_reset(self.cond, active_low=True),
            self.low_or_low,
            True,
            False,
        )

        gen_proc(
            ctx_low.and_reset(self.cond, active_low=True),
            self.low_and_low,
            True,
            False,
        )
        gen_proc(
            ctx_low.or_reset(self.cond, active_low=False),
            self.low_or_high,
            False,
            False,
        )
        gen_proc(
            ctx_low.and_reset(self.cond, active_low=False),
            self.low_and_high,
            False,
            False,
        )


#
# test code
#


@cocotb_util.test()
async def testbench_context_manager_04(dut: test_reset_builder_01):
    seq = cocotb_util.SequentialTest(dut.clk)

    reset = True
    cond = True

    def x(val, is_reset):
        exp = not is_reset
        if val.value != exp:
            assert (
                val.value == exp
            ), f"@ reset = {reset}, cond = {cond} : got = {val.value}, expected = {exp}"

    def check():
        x(dut.high_0.value, reset)
        x(dut.high_or_none.value, (reset or cond))
        x(dut.high_and_none.value, (reset and cond))
        x(dut.high_or_low.value, (reset or not cond))
        x(dut.high_and_low.value, (reset and not cond))
        x(dut.high_or_high.value, (reset or cond))
        x(dut.high_and_high.value, (reset and cond))

        x(dut.low_0.value, not reset)
        x(dut.low_or_none.value, (not reset) or cond)
        x(dut.low_and_none.value, (not reset) and cond)
        x(dut.low_or_low.value, (not reset) or not cond)
        x(dut.low_and_low.value, (not reset) and not cond)
        x(dut.low_or_high.value, (not reset) or cond)
        x(dut.low_and_high.value, (not reset) and cond)

    async def run_test():
        dut.reset.value = reset
        dut.cond.value = cond
        await seq.tick()
        await seq.tick()
        check()

    for reset in (True, False):
        for cond in (True, False):
            await run_test()

    await run_test()


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_reset_builder_01, __file__, self.__module__)
