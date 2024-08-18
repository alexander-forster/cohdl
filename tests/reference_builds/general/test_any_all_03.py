from __future__ import annotations

import unittest

import itertools

import cohdl
from cohdl import Bit, BitVector, Port, Unsigned
from cohdl import std

from cohdl_testutil import cocotb_util


class SimpleCustomType:
    def __init__(self, val):
        self.val = val

    def __bool__(self):
        return bool(self.val)


class ComplexCustomType:
    def __init__(self, val):
        self.val = val

    def __bool__(self):
        return self.val > 2


class test_any_all_03(cohdl.Entity):
    inp_a = Port.input(Bit)
    inp_b = Port.input(Bit)

    inp_bv1 = Port.input(Unsigned[2])
    inp_bv2 = Port.input(Unsigned[3])

    out_any_empty = Port.output(Bit)
    out_all_empty = Port.output(Bit)

    out_any_simple_a = Port.output(Bit)
    out_any_simple_b = Port.output(Bit)
    out_any_complex_a = Port.output(Bit)
    out_any_complex_b = Port.output(Bit)
    out_any_mixed_a = Port.output(Bit)
    out_any_mixed_b = Port.output(Bit)
    out_any_mixed_c = Port.output(Bit)
    out_any_mixed_d = Port.output(Bit)

    out_all_simple_a = Port.output(Bit)
    out_all_simple_b = Port.output(Bit)
    out_all_complex_a = Port.output(Bit)
    out_all_complex_b = Port.output(Bit)
    out_all_mixed_a = Port.output(Bit)
    out_all_mixed_b = Port.output(Bit)
    out_all_mixed_c = Port.output(Bit)
    out_all_mixed_d = Port.output(Bit)

    def architecture(self):
        @std.sequential(attributes={"zero_init_temporaries": True})
        def logic():
            self.out_any_empty <<= any([])
            self.out_all_empty <<= all(())

            self.out_any_simple_a <<= any(
                (SimpleCustomType(self.inp_a), SimpleCustomType(self.inp_b))
            )

            self.out_any_simple_a <<= any(
                (
                    SimpleCustomType(self.inp_a),
                    SimpleCustomType(self.inp_b),
                    SimpleCustomType(self.inp_bv1),
                    SimpleCustomType(self.inp_bv2),
                )
            )

            self.out_any_simple_b <<= any((SimpleCustomType(self.inp_a),))

            self.out_any_complex_a <<= any([ComplexCustomType(self.inp_bv1)])

            self.out_any_complex_b <<= any(
                [ComplexCustomType(self.inp_bv1), ComplexCustomType(self.inp_bv2)]
            )

            self.out_any_mixed_a <<= any(
                [
                    self.inp_a,
                    SimpleCustomType(self.inp_b),
                    ComplexCustomType(self.inp_bv2),
                ]
            )

            self.out_any_mixed_b <<= any(
                [
                    ComplexCustomType(self.inp_bv1),
                    self.inp_a,
                    SimpleCustomType(self.inp_b),
                ]
            )

            self.out_any_mixed_c <<= any(
                [
                    ComplexCustomType(self.inp_bv2),
                    self.inp_a,
                    SimpleCustomType(self.inp_b),
                    True,
                ]
            )

            self.out_any_mixed_d <<= any(
                [
                    False,
                    ComplexCustomType(self.inp_bv1),
                    self.inp_a,
                    SimpleCustomType(self.inp_b),
                ]
            )

            #
            #

            self.out_all_simple_a <<= all(
                (SimpleCustomType(self.inp_a), SimpleCustomType(self.inp_b))
            )

            self.out_all_simple_a <<= all(
                (
                    SimpleCustomType(self.inp_a),
                    SimpleCustomType(self.inp_b),
                    SimpleCustomType(self.inp_bv1),
                    SimpleCustomType(self.inp_bv2),
                )
            )

            self.out_all_simple_b <<= all((SimpleCustomType(self.inp_a),))

            self.out_all_complex_a <<= all([ComplexCustomType(self.inp_bv1)])

            self.out_all_complex_b <<= all(
                [ComplexCustomType(self.inp_bv1), ComplexCustomType(self.inp_bv2)]
            )

            self.out_all_mixed_a <<= all(
                [
                    self.inp_a,
                    SimpleCustomType(self.inp_b),
                    ComplexCustomType(self.inp_bv2),
                ]
            )

            self.out_all_mixed_b <<= all(
                [
                    ComplexCustomType(self.inp_bv1),
                    self.inp_a,
                    SimpleCustomType(self.inp_b),
                ]
            )

            self.out_all_mixed_c <<= all(
                [
                    ComplexCustomType(self.inp_bv2),
                    self.inp_a,
                    SimpleCustomType(self.inp_b),
                    True,
                ]
            )

            self.out_all_mixed_d <<= all(
                [
                    False,
                    ComplexCustomType(self.inp_bv1),
                    self.inp_a,
                    SimpleCustomType(self.inp_b),
                ]
            )


#
# test code
#


@cocotb_util.test()
async def testbench_any_all_03(dut: test_any_all_03):
    for a, b, bv1, bv2 in itertools.product(
        (0, 1), (0, 1), (0, 1, 2, 3), (0, 1, 2, 3, 4, 5, 6, 7)
    ):
        c1 = bv1 > 2
        c2 = bv2 > 2

        await cocotb_util.check_concurrent(
            [(dut.inp_a, a), (dut.inp_b, b), (dut.inp_bv1, bv1), (dut.inp_bv2, bv2)],
            [
                (dut.out_any_empty, any([])),
                (dut.out_all_empty, all([])),
                #
                (dut.out_any_simple_a, any([a, b, bv1, bv2])),
                (dut.out_any_simple_b, any([a])),
                (dut.out_any_complex_a, any([c1])),
                (dut.out_any_complex_b, any([c1, c2])),
                (dut.out_any_mixed_a, any([a, b, c2])),
                (dut.out_any_mixed_b, any([c1, a, b])),
                (dut.out_any_mixed_c, any([c2, a, b, True])),
                (dut.out_any_mixed_d, any([False, c1, a, b])),
                #
                (dut.out_all_simple_a, all([a, b, bv1, bv2])),
                (dut.out_all_simple_b, all([a])),
                (dut.out_all_complex_a, all([c1])),
                (dut.out_all_complex_b, all([c1, c2])),
                (dut.out_all_mixed_a, all([a, b, c2])),
                (dut.out_all_mixed_b, all([c1, a, b])),
                (dut.out_all_mixed_c, all([c2, a, b, True])),
                (dut.out_all_mixed_d, all([False, c1, a, b])),
            ],
        )


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_any_all_03, __file__, self.__module__)
