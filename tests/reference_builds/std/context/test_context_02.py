from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Signal, Unsigned
from cohdl import std

from cohdl_testutil import cocotb_util
from cohdl_testutil.cocotb_mock import MockBase


class test_context_02(cohdl.Entity):
    clk_a = Port.input(Bit)
    clk_b = Port.input(Bit)
    reset_a = Port.input(Bit)
    reset_b = Port.input(Bit)

    reset_or = Port.output(Bit)
    reset_and = Port.output(Bit)
    reset_and_or = Port.output(Bit)

    reset_expr_or = Port.output(Bit)
    reset_expr_and = Port.output(Bit)
    reset_expr_and_or = Port.output(Bit)

    def architecture(self):
        clk_a = std.Clock(self.clk_a)
        clk_b = std.Clock(self.clk_b)

        reset_a = std.Reset(self.reset_a)
        reset_b = std.Reset(self.reset_b, active_low=True, is_async=True)

        step_cond_b = lambda: Bit(True)

        ctx = std.Context(clk_a, reset_a)

        expr = lambda: self.reset_b

        ctx_or = ctx.or_reset(self.reset_b)
        ctx_and = ctx.and_reset(self.reset_b)
        ctx_and_or = ctx_and.or_reset(self.reset_b)

        ctx_expr_or = ctx.or_reset(expr=expr)
        ctx_expr_and = ctx.and_reset(expr=expr)
        ctx_expr_and_or = ctx_and.or_reset(expr=expr)

        std.concurrent_assign(self.reset_or, ctx_or.reset().signal())
        std.concurrent_assign(self.reset_and, ctx_and.reset().signal())
        std.concurrent_assign(self.reset_and_or, ctx_and_or.reset().signal())

        std.concurrent_assign(self.reset_expr_or, ctx_expr_or.reset().signal())
        std.concurrent_assign(self.reset_expr_and, ctx_expr_and.reset().signal())
        std.concurrent_assign(self.reset_expr_and_or, ctx_expr_and_or.reset().signal())

        #
        #
        #

        ctx_b = std.Context(clk_b, reset_b, step_cond=step_cond_b)

        ctx_new_a = ctx.or_reset(False)
        ctx_new_b = ctx_b.or_reset(False)

        assert ctx_new_a.reset().is_active_high() == True
        assert ctx_new_b.reset().is_active_high() == False
        assert ctx_new_a.reset().is_active_low() == False
        assert ctx_new_b.reset().is_active_low() == True
        assert ctx_new_a.reset().is_async() == False
        assert ctx_new_b.reset().is_async() == True

        ctx_new_a = ctx.or_reset(False, active_low=True)
        ctx_new_b = ctx_b.or_reset(False, active_low=False)

        assert ctx_new_a.reset().is_active_high() == False
        assert ctx_new_b.reset().is_active_high() == True
        assert ctx_new_a.reset().is_active_low() == True
        assert ctx_new_b.reset().is_active_low() == False
        assert ctx_new_a.reset().is_async() == False
        assert ctx_new_b.reset().is_async() == True

        ctx_new_a = ctx.or_reset(False, is_async=True)
        ctx_new_b = ctx_b.or_reset(False, active_low=False, is_async=False)

        assert ctx_new_a.reset().is_active_high() == True
        assert ctx_new_b.reset().is_active_high() == True
        assert ctx_new_a.reset().is_active_low() == False
        assert ctx_new_b.reset().is_active_low() == False
        assert ctx_new_a.reset().is_async() == True
        assert ctx_new_b.reset().is_async() == False

        #
        #
        #

        assert ctx.clk() is clk_a
        assert ctx.reset() is reset_a

        ctx_new = ctx.with_params()
        assert ctx_new.clk() is clk_a
        assert ctx_new.reset() is reset_a
        assert ctx_new.step_cond() is None

        ctx_new = ctx.with_params(clk=clk_b)
        assert ctx_new.clk() is clk_b
        assert ctx_new.reset() is reset_a
        assert ctx_new.step_cond() is None

        ctx_new = ctx.with_params(reset=reset_b)
        assert ctx_new.clk() is clk_a
        assert ctx_new.reset() is reset_b
        assert ctx_new.step_cond() is None

        ctx_new = ctx.with_params(step_cond=step_cond_b)
        assert ctx_new.clk() is clk_a
        assert ctx_new.reset() is reset_a
        assert ctx_new.step_cond() is step_cond_b

        ctx_new = ctx.with_params(clk=clk_b, reset=reset_b, step_cond=step_cond_b)
        assert ctx_new.clk() is clk_b
        assert ctx_new.reset() is reset_b
        assert ctx_new.step_cond() is step_cond_b


#
# test code
#


@cocotb_util.test()
async def testbench_context_02(dut: test_context_02):
    bool_opt = (0, 1)

    for ca in bool_opt:
        for cb in bool_opt:
            for ra in bool_opt:
                for rb in bool_opt:
                    dut.clk_a.value = ca
                    dut.clk_b.value = cb
                    dut.reset_a.value = ra
                    dut.reset_b.value = rb

                    await cocotb_util.step()

                    assert dut.reset_or == ra | rb
                    assert dut.reset_and == ra & rb
                    assert dut.reset_and_or == (ra & rb) | rb

                    assert dut.reset_expr_or == ra | rb
                    assert dut.reset_expr_and == ra & rb
                    assert dut.reset_expr_and_or == (ra & rb) | rb


class Unittest(unittest.TestCase):
    def test_all(self):
        cocotb_util.run_cocotb_tests(
            test_context_02,
            __file__,
            self.__module__,
        )
