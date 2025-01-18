from __future__ import annotations

import unittest

import cohdl
from cohdl import Port, Signed

from cohdl import std
from cohdl import op
from cohdl_testutil import cocotb_util

import os

CONSTANT: int = eval(os.getenv("cohdl_test_constant", "None"))


class test_operations_const(cohdl.Entity):

    input = Port.input(Signed[4])
    input_div = Port.input(Signed[4])

    op_add = Port.output(Signed[4])
    op_sub = Port.output(Signed[4])
    op_mul = Port.output(Signed[4])
    op_div = Port.output(Signed[4])
    op_mod = Port.output(Signed[4])
    op_rem = Port.output(Signed[4])

    op_add_2 = Port.output(Signed[4])
    op_sub_2 = Port.output(Signed[4])
    op_mul_2 = Port.output(Signed[4])
    op_div_2 = Port.output(Signed[4])
    op_mod_2 = Port.output(Signed[4])
    op_rem_2 = Port.output(Signed[4])

    def architecture(self):

        @std.concurrent
        def logic_simple():
            CONST_DIV = 1 if CONSTANT == 0 else CONSTANT

            self.op_add <<= self.input + CONSTANT
            self.op_sub <<= self.input - CONSTANT
            # self.op_mul <<= self.input * CONSTANT
            # self.op_div <<= op.truncdiv(self.input, CONST_DIV)
            # self.op_mod <<= self.input % CONST_DIV
            # self.op_rem <<= op.rem(self.input, CONST_DIV)

            self.op_add_2 <<= CONSTANT + self.input
            self.op_sub_2 <<= CONSTANT - self.input
            # self.op_mul_2 <<= CONSTANT * self.input
            # self.op_div_2 <<= op.truncdiv(CONSTANT, self.input_div)
            # self.op_mod_2 <<= CONSTANT % self.input_div
            # self.op_rem_2 <<= op.rem(CONSTANT, self.input_div)


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
                # (dut.op_mul, op_mul, "MUL"),
                # (dut.op_mul_2, op_mul, "MUL2"),
                # (dut.op_div, op_div),
                # (dut.op_div_2, op_div_2),
                # (dut.op_mod, op_mod, "MOD"),
                # (dut.op_mod_2, op_mod_2, "MOD2"),
                # (dut.op_rem, op_rem, "REM"),
                # (dut.op_rem_2, op_rem_2, "REM2"),
            ],
            f"inp = {input} + {CONSTANT} = {op_rem_2}",
        )


class Unittest(unittest.TestCase):
    def test_operations_1(self):
        global CONSTANT
        CONSTANT = 1
        cocotb_util.run_cocotb_tests(
            test_operations_const,
            __file__,
            self.__module__,
            extra_env={"cohdl_test_constant": "1"},
        )

    def test_operations_2(self):
        global CONSTANT
        CONSTANT = 2
        cocotb_util.run_cocotb_tests(
            test_operations_const,
            __file__,
            self.__module__,
            extra_env={"cohdl_test_constant": "2"},
        )

    def test_operations_7(self):
        global CONSTANT
        CONSTANT = 7
        cocotb_util.run_cocotb_tests(
            test_operations_const,
            __file__,
            self.__module__,
            extra_env={"cohdl_test_constant": "7"},
        )

    def test_operations__1(self):
        global CONSTANT
        CONSTANT = -1
        cocotb_util.run_cocotb_tests(
            test_operations_const,
            __file__,
            self.__module__,
            extra_env={"cohdl_test_constant": "-1"},
        )

    def test_operations__8(self):
        global CONSTANT
        CONSTANT = -8
        cocotb_util.run_cocotb_tests(
            test_operations_const,
            __file__,
            self.__module__,
            extra_env={"cohdl_test_constant": "-8"},
        )
