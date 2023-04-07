from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Unsigned, true, false

from cohdl import std

from cohdl_testutil import cocotb_util


class test_booleans_01(cohdl.Entity):
    input_bit = Port.input(Bit)
    input_bool = Port.input(bool)

    inp_unsigned_a = Port.input(Unsigned[4])
    inp_unsigned_b = Port.input(Unsigned[4])
    inp_unsigned_c = Port.input(Unsigned[4])

    inp_bv_a = Port.input(BitVector[3])
    inp_bv_b = Port.input(BitVector[3])

    output_bit = Port.output(Bit)
    output_bool = Port.output(bool)

    output_bit_2 = Port.output(Bit)
    output_bool_2 = Port.output(bool)

    output_bit_true = Port.output(Bit)
    output_bool_true = Port.output(bool)
    output_bit_true_int = Port.output(Bit)
    output_bool_true_int = Port.output(bool)
    output_bit_true_str = Port.output(Bit)
    output_bool_true_str = Port.output(bool)
    output_bit_true_cohdl_true = Port.output(Bit)
    output_bool_true_cohdl_true = Port.output(bool)

    output_bit_false = Port.output(Bit)
    output_bool_false = Port.output(bool)
    output_bit_false_int = Port.output(Bit)
    output_bool_false_int = Port.output(bool)
    output_bit_false_str = Port.output(Bit)
    output_bool_false_str = Port.output(bool)
    output_bit_true_cohdl_false = Port.output(Bit)
    output_bool_true_cohdl_false = Port.output(bool)

    cmp_eq_bit = Port.output(Bit)
    cmp_eq_bool = Port.output(bool)
    cmp_gt_bit = Port.output(Bit)
    cmp_gt_bool = Port.output(bool)
    cmp_lt_bit = Port.output(Bit)
    cmp_lt_bool = Port.output(bool)
    cmp_ge_bit = Port.output(Bit)
    cmp_ge_bool = Port.output(bool)
    cmp_le_bit = Port.output(Bit)
    cmp_le_bool = Port.output(bool)

    cmp_bv_eq_bit = Port.output(Bit)
    cmp_bv_eq_bool = Port.output(bool)
    cmp_bv_ne_bit = Port.output(Bit)
    cmp_bv_ne_bool = Port.output(bool)

    cmp_range_bit = Port.output(Bit)
    cmp_range_bool = Port.output(bool)

    def architecture(self):
        @std.concurrent
        def logic_simple():
            # check assignment of bool/bit to self type
            self.output_bit <<= self.input_bit
            self.output_bool <<= self.input_bool

            # check assignment of bool/bit to other type
            self.output_bit_2 <<= self.input_bool
            self.output_bool_2 <<= self.input_bit

            # assign constant values
            self.output_bit_true <<= True
            self.output_bool_true <<= True
            self.output_bit_true_int <<= 1
            self.output_bool_true_int <<= 1
            self.output_bit_true_str <<= "1"
            self.output_bool_true_str <<= "1"
            self.output_bit_true_cohdl_true <<= true
            self.output_bool_true_cohdl_true <<= true
            self.output_bit_false <<= False
            self.output_bool_false <<= False
            self.output_bit_false_int <<= 0
            self.output_bool_false_int <<= 0
            self.output_bit_false_str <<= "0"
            self.output_bool_false_str <<= "0"
            self.output_bit_true_cohdl_false <<= false
            self.output_bool_true_cohdl_false <<= false

            # compare unsigned values
            self.cmp_eq_bit <<= self.inp_unsigned_a == self.inp_unsigned_b
            self.cmp_eq_bool <<= self.inp_unsigned_a == self.inp_unsigned_b

            self.cmp_gt_bit <<= self.inp_unsigned_a > self.inp_unsigned_b
            self.cmp_gt_bool <<= self.inp_unsigned_a > self.inp_unsigned_b

            self.cmp_lt_bit <<= self.inp_unsigned_a < self.inp_unsigned_b
            self.cmp_lt_bool <<= self.inp_unsigned_a < self.inp_unsigned_b

            self.cmp_ge_bit <<= self.inp_unsigned_a >= self.inp_unsigned_b
            self.cmp_ge_bool <<= self.inp_unsigned_a >= self.inp_unsigned_b

            self.cmp_le_bit <<= self.inp_unsigned_a <= self.inp_unsigned_b
            self.cmp_le_bool <<= self.inp_unsigned_a <= self.inp_unsigned_b

            # compare bitvectors
            self.cmp_bv_eq_bit <<= self.inp_bv_a == self.inp_bv_b
            self.cmp_bv_eq_bool <<= self.inp_bv_a == self.inp_bv_b

            self.cmp_bv_ne_bit <<= self.inp_bv_a != self.inp_bv_b
            self.cmp_bv_ne_bool <<= self.inp_bv_a != self.inp_bv_b

            # check pythons sequence of comparison operators
            self.cmp_range_bit <<= (
                self.inp_unsigned_a < self.inp_unsigned_b < self.inp_unsigned_c
            )
            self.cmp_range_bool <<= (
                self.inp_unsigned_a < self.inp_unsigned_b < self.inp_unsigned_c
            )


#
# test code
#


@cocotb_util.test()
async def testbench_functions(dut: test_booleans_01):
    for a in range(16):
        for b in range(16):
            for c in range(16):
                inp_bit = a & 1
                inp_bool = b & 1

                eq = a == b
                gt = a > b
                lt = a < b
                ge = a >= b
                le = a <= b

                bv_a = a & 0b111
                bv_b = a & 0b111

                bv_eq = bv_a == bv_b
                bv_ne = bv_a != bv_a

                cmp_range = a < b < c

                await cocotb_util.check_concurrent(
                    [
                        (dut.input_bit, inp_bit),
                        (dut.input_bool, inp_bool),
                        (dut.inp_unsigned_a, a),
                        (dut.inp_unsigned_b, b),
                        (dut.inp_unsigned_c, c),
                        (dut.inp_bv_a, bv_a),
                        (dut.inp_bv_b, bv_b),
                    ],
                    [
                        # direct assignments
                        (dut.output_bit, inp_bit),
                        (dut.output_bool, inp_bool),
                        (dut.output_bit_2, inp_bool),
                        (dut.output_bool_2, inp_bit),
                        # constant assignments
                        (dut.output_bit_true, 1),
                        (dut.output_bool_true, 1),
                        (dut.output_bit_true_int, 1),
                        (dut.output_bool_true_int, 1),
                        (dut.output_bit_true_str, 1),
                        (dut.output_bool_true_str, 1),
                        (dut.output_bit_true_cohdl_true, 1),
                        (dut.output_bool_true_cohdl_true, 1),
                        (dut.output_bit_false, 0),
                        (dut.output_bool_false, 0),
                        (dut.output_bit_false_int, 0),
                        (dut.output_bool_false_int, 0),
                        (dut.output_bit_false_str, 0),
                        (dut.output_bool_false_str, 0),
                        (dut.output_bit_true_cohdl_false, 0),
                        (dut.output_bool_true_cohdl_false, 0),
                        # comparisons unsigned
                        (dut.cmp_eq_bit, eq),
                        (dut.cmp_eq_bool, eq),
                        (dut.cmp_gt_bit, gt),
                        (dut.cmp_gt_bool, gt),
                        (dut.cmp_lt_bit, lt),
                        (dut.cmp_lt_bool, lt),
                        (dut.cmp_ge_bit, ge),
                        (dut.cmp_ge_bool, ge),
                        (dut.cmp_le_bit, le),
                        (dut.cmp_le_bool, le),
                        # # comparisons bitvector
                        (dut.cmp_bv_eq_bit, bv_eq),
                        (dut.cmp_bv_eq_bool, bv_eq),
                        (dut.cmp_bv_ne_bit, bv_ne),
                        (dut.cmp_bv_ne_bool, bv_ne),
                        (dut.cmp_range_bit, cmp_range),
                        (dut.cmp_range_bool, cmp_range),
                    ],
                )


class Unittest(unittest.TestCase):
    def test_functions(self):
        cocotb_util.run_cocotb_tests(test_booleans_01, __file__, self.__module__)
