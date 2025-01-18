from __future__ import annotations

import unittest

import cohdl
from cohdl import Port, Unsigned

from cohdl import std
from cohdl import op
from cohdl_testutil import cocotb_util

import os

CONSTANT: int = eval(os.getenv("cohdl_test_constant", "None"))
MAKE_UNSIGNED: bool = eval(os.getenv("cohdl_test_make_unsigned", "None"))


class test_operations_const(cohdl.Entity):

    input = Port.input(Unsigned[4])
    input_div = Port.input(Unsigned[4])

    op_add = Port.output(Unsigned[4])
    op_sub = Port.output(Unsigned[4])
    op_mul = Port.output(Unsigned[8])
    op_div = Port.output(Unsigned[4])
    op_tdiv = Port.output(Unsigned[4])
    op_mod = Port.output(Unsigned[4])
    op_rem = Port.output(Unsigned[4])

    op_add_2 = Port.output(Unsigned[4])
    op_sub_2 = Port.output(Unsigned[4])
    op_mul_2 = Port.output(Unsigned[8])
    op_div_2 = Port.output(Unsigned[4])
    op_mod_2 = Port.output(Unsigned[4])

    def architecture(self):
        global CONSTANT

        CONST_DIV = 1 if CONSTANT == 0 else CONSTANT

        if MAKE_UNSIGNED:
            CONSTANT = Unsigned[4](CONSTANT)
            CONST_DIV = Unsigned[4](CONST_DIV)

        @std.concurrent
        def logic_simple():
            CONST_DIV = 1 if CONSTANT == 0 else CONSTANT

            self.op_add <<= self.input + CONSTANT
            self.op_sub <<= self.input - CONSTANT
            self.op_mul <<= self.input * CONSTANT

            if MAKE_UNSIGNED:
                self.op_div <<= self.input // CONST_DIV
            else:
                self.op_div <<= op.truncdiv(self.input, CONST_DIV)

            self.op_tdiv <<= op.truncdiv(self.input, CONST_DIV)
            self.op_mod <<= self.input % CONST_DIV
            self.op_rem <<= op.rem(self.input, CONST_DIV)

            self.op_add_2 <<= CONSTANT + self.input
            self.op_sub_2 <<= CONSTANT - self.input
            self.op_mul_2 <<= CONSTANT * self.input

            if MAKE_UNSIGNED:
                self.op_div_2 <<= CONSTANT // self.input_div
            else:
                self.op_div_2 <<= op.truncdiv(CONSTANT, self.input_div)

            self.op_mod_2 <<= CONSTANT % self.input_div


#
# test code
#


@cocotb_util.test()
async def testbench_operations_const(dut: test_operations_const):

    CONSTANT_DIV = 1 if CONSTANT == 0 else CONSTANT

    for input in range(16):
        input_div = 1 if input == 0 else input

        op_add = (input + CONSTANT) % 16
        op_sub = (input - CONSTANT + 16) % 16
        op_sub_2 = (CONSTANT - input + 16) % 16

        op_mul = input * CONSTANT

        op_div = input // CONSTANT_DIV
        op_div_2 = CONSTANT // input_div

        op_mod = input % CONSTANT_DIV
        op_mod_2 = CONSTANT % input_div

        await cocotb_util.check_concurrent(
            [(dut.input, input), (dut.input_div, input_div)],
            [
                (dut.op_add, op_add, "ADD"),
                (dut.op_add_2, op_add, "ADD2"),
                (dut.op_sub, op_sub, "SUB"),
                (dut.op_sub_2, op_sub_2, "SUB2"),
                (dut.op_mul, op_mul, "MUL"),
                (dut.op_mul_2, op_mul, "MUL2"),
                (dut.op_div, op_div, "DIV"),
                (dut.op_div_2, op_div_2, "DIV2"),
                (dut.op_mod, op_mod, "MOD"),
                (dut.op_mod_2, op_mod_2, "MOD2"),
            ],
        )


class Unittest(unittest.TestCase):

    def _perform_test(self, val):
        for make_unsigned in (True, False):
            global CONSTANT, MAKE_UNSIGNED
            CONSTANT = val
            MAKE_UNSIGNED = make_unsigned

            cocotb_util.run_cocotb_tests(
                test_operations_const,
                __file__,
                self.__module__,
                extra_env={
                    "cohdl_test_constant": repr(val),
                    "cohdl_test_make_unsigned": repr(make_unsigned),
                },
            )

    def test_operations(self):
        for val in (1, 2, 3, 6, 13, 14, 15):
            self._perform_test(val)
