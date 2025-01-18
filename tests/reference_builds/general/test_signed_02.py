from __future__ import annotations

import unittest

import cohdl
from cohdl import Port, Signed

from cohdl import std
from cohdl import op
from cohdl_testutil import cocotb_util

import os

CONSTANT: int = eval(os.getenv("cohdl_test_constant", "None"))
MAKE_SIGNED: bool = eval(os.getenv("cohdl_test_make_signed", "None"))


class test_operations_const(cohdl.Entity):

    input = Port.input(Signed[4])
    input_div = Port.input(Signed[4])

    op_add = Port.output(Signed[4])
    op_sub = Port.output(Signed[4])
    op_mul = Port.output(Signed[8])
    op_div = Port.output(Signed[4])
    op_mod = Port.output(Signed[4])
    op_rem = Port.output(Signed[4])

    op_add_2 = Port.output(Signed[4])
    op_sub_2 = Port.output(Signed[4])
    op_mul_2 = Port.output(Signed[8])
    op_div_2 = Port.output(Signed[4])
    op_mod_2 = Port.output(Signed[4])
    op_rem_2 = Port.output(Signed[4])

    def architecture(self):
        global CONSTANT

        CONST_DIV = 1 if CONSTANT == 0 else CONSTANT

        if MAKE_SIGNED:
            CONSTANT = Signed[4](CONSTANT)
            CONST_DIV = Signed[4](CONST_DIV)

        @std.concurrent
        def logic_simple():

            self.op_add <<= self.input + CONSTANT
            self.op_sub <<= self.input - CONSTANT
            self.op_mul <<= self.input * CONSTANT
            self.op_div <<= op.truncdiv(self.input, CONST_DIV)
            self.op_mod <<= self.input % CONST_DIV
            self.op_rem <<= op.rem(self.input, CONST_DIV)

            self.op_add_2 <<= CONSTANT + self.input
            self.op_sub_2 <<= CONSTANT - self.input
            self.op_mul_2 <<= CONSTANT * self.input
            self.op_div_2 <<= op.truncdiv(CONSTANT, self.input_div)
            self.op_mod_2 <<= CONSTANT % self.input_div
            self.op_rem_2 <<= op.rem(CONSTANT, self.input_div)


#
# test code
#


def c_like_div(a, b):
    div = int(a / b)
    mod = a % b
    rem = a - b * div
    return div, mod, rem


@cocotb_util.test()
async def testbench_operations_const(dut: test_operations_const):
    CONSTANT_DIV = 1 if CONSTANT == 0 else CONSTANT

    for input in range(-8, 7):
        input_div = 1 if input == 0 else input

        op_add = (input + CONSTANT) % 16
        op_sub = (input - CONSTANT + 16) % 16
        op_sub_2 = (CONSTANT - input + 16) % 16

        op_mul = input * CONSTANT

        op_div, op_mod, op_rem = c_like_div(input, CONSTANT_DIV)
        op_div_2, op_mod_2, op_rem_2 = c_like_div(CONSTANT, input_div)

        assert (op.add(input, CONSTANT) % 16) == op_add
        assert ((op.sub(input, CONSTANT) + 16) % 16) == op_sub
        assert ((op.sub(CONSTANT, input) + 16) % 16) == op_sub_2
        assert op.mul(input, CONSTANT) == op_mul

        assert op.truncdiv(input, CONSTANT_DIV) == op_div
        assert op.mod(input, CONSTANT_DIV) == op_mod
        assert op.rem(input, CONSTANT_DIV) == op_rem

        assert op.truncdiv(CONSTANT, input_div) == op_div_2
        assert op.mod(CONSTANT, input_div) == op_mod_2
        assert op.rem(CONSTANT, input_div) == op_rem_2

        await cocotb_util.check_concurrent(
            [
                (dut.input, input),
                (dut.input_div, input_div),
            ],
            [
                (dut.op_add, op_add, "ADD"),
                (dut.op_add_2, op_add, "ADD2"),
                (dut.op_sub, op_sub, "SUB"),
                (dut.op_sub_2, op_sub_2, "SUB2"),
                (dut.op_mul, op_mul, "MUL"),
                (dut.op_mul_2, op_mul, "MUL2"),
                (dut.op_div, op_div),
                (dut.op_div_2, op_div_2),
                (dut.op_mod, op_mod, "MOD"),
                (dut.op_mod_2, op_mod_2, "MOD2"),
                (dut.op_rem, op_rem, "REM"),
                (dut.op_rem_2, op_rem_2, "REM2"),
            ],
            f"inp = {CONSTANT} rem {input_div} = {op_rem_2}",
        )


class Unittest(unittest.TestCase):
    def _perform_test(self, val):
        for make_signed in (True, False):

            global CONSTANT, MAKE_SIGNED
            CONSTANT = val
            MAKE_SIGNED = make_signed

            cocotb_util.run_cocotb_tests(
                test_operations_const,
                __file__,
                self.__module__,
                extra_env={
                    "cohdl_test_constant": repr(val),
                    "cohdl_test_make_signed": repr(make_signed),
                },
            )

    def test_operations(self):
        for val in (1, -1, 2, -2, -8, -7, 7, 4):
            self._perform_test(val)
