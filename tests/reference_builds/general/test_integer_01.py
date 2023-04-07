from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Unsigned, Signal, Signed

from cohdl import std

from cohdl_testutil import cocotb_util


class test_integer_01(cohdl.Entity):
    inp_a = Port.input(Unsigned[16])
    inp_b = Port.input(Unsigned[16])

    inp_a_s = Port.input(Signed[16])
    inp_b_s = Port.input(Signed[16])

    out_sum = Port.output(Unsigned[16], default=0)
    out_dif = Port.output(Signed[16], default=0)

    cmp_eq_i_i = Port.output(bool)
    cmp_eq_u_i = Port.output(bool)
    cmp_eq_i_u = Port.output(bool)
    cmp_eq_s_i = Port.output(bool)
    cmp_eq_i_s = Port.output(bool)

    cmp_ne_i_i = Port.output(bool)
    cmp_ne_u_i = Port.output(bool)
    cmp_ne_i_u = Port.output(bool)
    cmp_ne_s_i = Port.output(bool)
    cmp_ne_i_s = Port.output(bool)

    cmp_gt_i_i = Port.output(bool)
    cmp_gt_u_i = Port.output(bool)
    cmp_gt_i_u = Port.output(bool)
    cmp_gt_s_i = Port.output(bool)
    cmp_gt_i_s = Port.output(bool)

    cmp_lt_i_i = Port.output(bool)
    cmp_lt_u_i = Port.output(bool)
    cmp_lt_i_u = Port.output(bool)
    cmp_lt_s_i = Port.output(bool)
    cmp_lt_i_s = Port.output(bool)

    cmp_ge_i_i = Port.output(bool)
    cmp_ge_u_i = Port.output(bool)
    cmp_ge_i_u = Port.output(bool)
    cmp_ge_s_i = Port.output(bool)
    cmp_ge_i_s = Port.output(bool)

    cmp_le_i_i = Port.output(bool)
    cmp_le_u_i = Port.output(bool)
    cmp_le_i_u = Port.output(bool)
    cmp_le_s_i = Port.output(bool)
    cmp_le_i_s = Port.output(bool)

    def architecture(self):
        int_a = Signal[int](0)
        int_b = Signal[int](0)
        int_a_s = Signal[int](0)
        int_b_s = Signal[int](0)

        int_sum = Signal[int](0)
        int_dif = Signal[int](0)

        @std.concurrent(attributes={"zero_init_temporaries": True})
        def logic_simple():
            nonlocal int_a, int_b, int_sum, int_dif, int_a_s, int_b_s
            int_a <<= self.inp_a
            int_b <<= self.inp_b

            int_a_s <<= self.inp_a_s
            int_b_s <<= self.inp_b_s

            # integer calculations
            int_sum <<= int_a + int_b
            int_dif <<= int_a_s - int_b_s

            # assign integer results to signed/unsigned ports
            # required by ghdl
            self.out_sum <<= int_sum
            self.out_dif <<= int_dif

            # eq
            self.cmp_eq_i_i <<= int_a == int_b
            self.cmp_eq_i_u <<= int_a == self.inp_b
            self.cmp_eq_u_i <<= self.inp_a == int_b
            self.cmp_eq_i_s <<= int_a_s == self.inp_b_s
            self.cmp_eq_s_i <<= self.inp_a_s == int_b_s

            # ne
            self.cmp_ne_i_i <<= int_a != int_b
            self.cmp_ne_i_u <<= int_a != self.inp_b
            self.cmp_ne_u_i <<= self.inp_a != int_b
            self.cmp_ne_i_s <<= int_a_s != self.inp_b_s
            self.cmp_ne_s_i <<= self.inp_a_s != int_b_s
            # gt
            self.cmp_gt_i_i <<= int_a > int_b
            self.cmp_gt_i_u <<= int_a > self.inp_b
            self.cmp_gt_u_i <<= self.inp_a > int_b
            self.cmp_gt_i_s <<= int_a_s > self.inp_b_s
            self.cmp_gt_s_i <<= self.inp_a_s > int_b_s
            # lt
            self.cmp_lt_i_i <<= int_a < int_b
            self.cmp_lt_i_u <<= int_a < self.inp_b
            self.cmp_lt_u_i <<= self.inp_a < int_b
            self.cmp_lt_i_s <<= int_a_s < self.inp_b_s
            self.cmp_lt_s_i <<= self.inp_a_s < int_b_s
            # ge
            self.cmp_ge_i_i <<= int_a >= int_b
            self.cmp_ge_i_u <<= int_a >= self.inp_b
            self.cmp_ge_u_i <<= self.inp_a >= int_b
            self.cmp_ge_i_s <<= int_a_s >= self.inp_b_s
            self.cmp_ge_s_i <<= self.inp_a_s >= int_b_s
            # le
            self.cmp_le_i_i <<= int_a <= int_b
            self.cmp_le_i_u <<= int_a <= self.inp_b
            self.cmp_le_u_i <<= self.inp_a <= int_b
            self.cmp_le_i_s <<= int_a_s <= self.inp_b_s
            self.cmp_le_s_i <<= self.inp_a_s <= int_b_s


@cocotb_util.test()
async def testbench_functions(dut: test_integer_01):
    for a in range(16):
        for b in range(16):
            a_s = a - 8
            b_s = b - 8

            await cocotb_util.check_concurrent(
                [
                    (dut.inp_a, a),
                    (dut.inp_b, b),
                    (dut.inp_a_s, a_s),
                    (dut.inp_b_s, b_s),
                ],
                [
                    (dut.out_sum, a + b),
                    (dut.out_dif, a_s - b_s),
                    # eq
                    (dut.cmp_eq_i_i, a == b),
                    (dut.cmp_eq_i_u, a == b),
                    (dut.cmp_eq_u_i, a == b),
                    (dut.cmp_eq_i_s, a_s == b_s),
                    (dut.cmp_eq_s_i, a_s == b_s),
                    # ne
                    (dut.cmp_ne_i_i, a != b),
                    (dut.cmp_ne_i_u, a != b),
                    (dut.cmp_ne_u_i, a != b),
                    (dut.cmp_ne_i_s, a_s != b_s),
                    (dut.cmp_ne_s_i, a_s != b_s),
                    # gt
                    (dut.cmp_gt_i_i, a > b),
                    (dut.cmp_gt_i_u, a > b),
                    (dut.cmp_gt_u_i, a > b),
                    (dut.cmp_gt_i_s, a_s > b_s),
                    (dut.cmp_gt_s_i, a_s > b_s),
                    # lt
                    (dut.cmp_lt_i_i, a < b),
                    (dut.cmp_lt_i_u, a < b),
                    (dut.cmp_lt_u_i, a < b),
                    (dut.cmp_lt_i_s, a_s < b_s),
                    (dut.cmp_lt_s_i, a_s < b_s),
                    # ge
                    (dut.cmp_ge_i_i, a >= b),
                    (dut.cmp_ge_i_u, a >= b),
                    (dut.cmp_ge_u_i, a >= b),
                    (dut.cmp_ge_i_s, a_s >= b_s),
                    (dut.cmp_ge_s_i, a_s >= b_s),
                    # le
                    (dut.cmp_le_i_i, a <= b),
                    (dut.cmp_le_i_u, a <= b),
                    (dut.cmp_le_u_i, a <= b),
                    (dut.cmp_le_i_s, a_s <= b_s),
                    (dut.cmp_le_s_i, a_s <= b_s),
                ],
            )


class Unittest(unittest.TestCase):
    def test_functions(self):
        cocotb_util.run_cocotb_tests(test_integer_01, __file__, self.__module__)
