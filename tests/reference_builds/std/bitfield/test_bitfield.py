from __future__ import annotations

import unittest

import cohdl
from cohdl import std, Bit, BitVector, Port, Unsigned, Signed

from cohdl.std.bitfield import BitField, Field

import cohdl_testutil
from cohdl_testutil import cocotb_util

import random
import cocotb


class SimpleBitField(BitField[16]):
    a: Field[0]
    b: Field[1]
    c: Field[4:2]
    d: Field[15:0]
    e: Field[3:0].Unsigned

    def check_fields(self):
        assert self._width_ == 16
        assert SimpleBitField._width_ == 16
        assert std.instance_check(self.a, Bit)
        assert std.instance_check(self.b, Bit)
        assert std.instance_check(self.c, BitVector[3])
        assert std.instance_check(self.d, BitVector[16])
        assert std.instance_check(self.e, Unsigned[4])


class NestedInner(BitField[4]):
    all: Field[3:0]
    a: Field[0]
    b: Field[3:0].Signed
    c: Field[2:0].Unsigned

    def check_fields(self):
        assert self._width_ == 4
        assert NestedInner._width_ == 4
        assert std.instance_check(self.all, BitVector[4])
        assert std.instance_check(self.a, Bit)
        assert std.instance_check(self.b, Signed[4])
        assert std.instance_check(self.c, Unsigned[3])


class InnerBitField(BitField[8]):
    all: Field[7:0]

    nested_1: NestedInner[0]
    nested_2: NestedInner[0]

    nested_3: NestedInner[2]

    def check_fields(self):
        assert self._width_ == 8
        assert InnerBitField._width_ == 8
        assert std.instance_check(self.all, BitVector[7:0])
        assert std.instance_check(self.nested_1, NestedInner)
        assert std.instance_check(self.nested_1, NestedInner[0])
        assert std.instance_check(self.nested_2, NestedInner)
        assert std.instance_check(self.nested_2, NestedInner[0])
        assert std.instance_check(self.nested_3, NestedInner)
        assert std.instance_check(self.nested_3, NestedInner[2])
        assert not std.instance_check(self.nested_3, NestedInner[0])


class OuterBitField(BitField[16]):
    inner_1: InnerBitField[0]
    inner_2: InnerBitField[15:8]

    def check_fields(self):
        assert self._width_ == 16
        assert OuterBitField._width_ == 16
        assert std.instance_check(self.inner_1, InnerBitField)
        assert std.instance_check(self.inner_1, InnerBitField[0])
        assert std.instance_check(self.inner_2, InnerBitField)
        assert std.instance_check(self.inner_2, InnerBitField[8])

        self.inner_1.check_fields()
        self.inner_2.check_fields()


class test_bitfield(cohdl.Entity):
    inp_vector = Port.input(BitVector[16])

    simple_a = Port.output(Bit)
    simple_b = Port.output(Bit)
    simple_c = Port.output(BitVector[3])
    simple_d = Port.output(BitVector[16])
    simple_e = Port.output(BitVector[4])

    #
    #

    outer_inner1_all = Port.output(BitVector[8])
    outer_inner1_nested1_all = Port.output(BitVector[4])
    outer_inner1_nested1_a = Port.output(Bit)
    outer_inner1_nested1_b = Port.output(Signed[4])
    outer_inner1_nested1_c = Port.output(Unsigned[3])
    outer_inner1_nested2_all = Port.output(BitVector[4])
    outer_inner1_nested2_a = Port.output(Bit)
    outer_inner1_nested2_b = Port.output(Signed[4])
    outer_inner1_nested2_c = Port.output(Unsigned[3])
    outer_inner1_nested3_all = Port.output(BitVector[4])
    outer_inner1_nested3_a = Port.output(Bit)
    outer_inner1_nested3_b = Port.output(Signed[4])
    outer_inner1_nested3_c = Port.output(Unsigned[3])

    outer_inner2_all = Port.output(BitVector[8])
    outer_inner2_nested1_all = Port.output(BitVector[4])
    outer_inner2_nested1_a = Port.output(Bit)
    outer_inner2_nested1_b = Port.output(Signed[4])
    outer_inner2_nested1_c = Port.output(Unsigned[3])
    outer_inner2_nested2_all = Port.output(BitVector[4])
    outer_inner2_nested2_a = Port.output(Bit)
    outer_inner2_nested2_b = Port.output(Signed[4])
    outer_inner2_nested2_c = Port.output(Unsigned[3])
    outer_inner2_nested3_all = Port.output(BitVector[4])
    outer_inner2_nested3_a = Port.output(Bit)
    outer_inner2_nested3_b = Port.output(Signed[4])
    outer_inner2_nested3_c = Port.output(Unsigned[3])

    #
    #

    def architecture(self):
        simple = SimpleBitField(self.inp_vector)
        simple_sig = std.Signal[SimpleBitField]()

        simple.check_fields()
        simple_sig.check_fields()

        @std.concurrent
        def logic_simple():
            nonlocal simple_sig
            simple.check_fields()
            simple_sig.check_fields()

            simple_sig <<= simple

            self.simple_a <<= simple_sig.a
            self.simple_b <<= simple_sig.b
            self.simple_c <<= simple_sig.c
            self.simple_d <<= simple_sig.d
            self.simple_e <<= simple_sig.e

        outer = std.Ref[OuterBitField](self.inp_vector)

        outer.check_fields()

        @std.sequential
        def logic_outer():
            outer_var = std.Variable(outer)

            outer.check_fields()
            outer_var.check_fields()

            outer_var.inner_1 @= outer.inner_1
            outer_var.inner_2.all @= outer.inner_2.all

            #
            #

            self.outer_inner1_all <<= outer_var.inner_1.all

            self.outer_inner1_nested1_all <<= outer_var.inner_1.nested_1.all
            self.outer_inner1_nested1_a <<= outer_var.inner_1.nested_1.a
            self.outer_inner1_nested1_b <<= outer_var.inner_1.nested_1.b
            self.outer_inner1_nested1_c <<= outer_var.inner_1.nested_1.c

            self.outer_inner1_nested2_all <<= outer_var.inner_1.nested_2.all
            self.outer_inner1_nested2_a <<= outer_var.inner_1.nested_2.a
            self.outer_inner1_nested2_b <<= outer_var.inner_1.nested_2.b
            self.outer_inner1_nested2_c <<= outer_var.inner_1.nested_2.c

            self.outer_inner1_nested3_all <<= outer_var.inner_1.nested_3.all
            self.outer_inner1_nested3_a <<= outer_var.inner_1.nested_3.a
            self.outer_inner1_nested3_b <<= outer_var.inner_1.nested_3.b
            self.outer_inner1_nested3_c <<= outer_var.inner_1.nested_3.c

            #
            #

            self.outer_inner2_all <<= outer_var.inner_2.all

            self.outer_inner2_nested1_all <<= outer_var.inner_2.nested_1.all
            self.outer_inner2_nested1_a <<= outer_var.inner_2.nested_1.a
            self.outer_inner2_nested1_b <<= outer_var.inner_2.nested_1.b
            self.outer_inner2_nested1_c <<= outer_var.inner_2.nested_1.c

            self.outer_inner2_nested2_all <<= outer_var.inner_2.nested_2.all
            self.outer_inner2_nested2_a <<= outer_var.inner_2.nested_2.a
            self.outer_inner2_nested2_b <<= outer_var.inner_2.nested_2.b
            self.outer_inner2_nested2_c <<= outer_var.inner_2.nested_2.c

            self.outer_inner2_nested3_all <<= outer_var.inner_2.nested_3.all
            self.outer_inner2_nested3_a <<= outer_var.inner_2.nested_3.a
            self.outer_inner2_nested3_b <<= outer_var.inner_2.nested_3.b
            self.outer_inner2_nested3_c <<= outer_var.inner_2.nested_3.c


def subvec(inp: int, msb, lsb):
    mask = (2 << msb) - 1
    return (inp & mask) >> lsb


@cocotb.test()
async def testbench_function_simple(dut: test_bitfield):
    for _ in range(100):
        test_value = random.randint(0, 2**16 - 1)

        await cocotb_util.check_concurrent(
            [(dut.inp_vector, test_value)],
            [
                (dut.simple_a, subvec(test_value, 0, 0)),
                (dut.simple_b, subvec(test_value, 1, 1)),
                (dut.simple_c, subvec(test_value, 4, 2)),
                (dut.simple_d, subvec(test_value, 15, 0)),
                (dut.simple_e, subvec(test_value, 3, 0)),
                #
                (dut.outer_inner1_all, subvec(test_value, 7, 0)),
                (dut.outer_inner1_nested1_all, subvec(test_value, 3, 0)),
                (dut.outer_inner1_nested1_a, subvec(test_value, 0, 0)),
                (dut.outer_inner1_nested1_b, subvec(test_value, 3, 0)),
                (dut.outer_inner1_nested1_c, subvec(test_value, 2, 0)),
                #
                (dut.outer_inner1_nested2_all, subvec(test_value, 3, 0)),
                (dut.outer_inner1_nested2_a, subvec(test_value, 0, 0)),
                (dut.outer_inner1_nested2_b, subvec(test_value, 3, 0)),
                (dut.outer_inner1_nested2_c, subvec(test_value, 2, 0)),
                #
                (dut.outer_inner1_nested3_all, subvec(test_value, 5, 2)),
                (dut.outer_inner1_nested3_a, subvec(test_value, 2, 2)),
                (dut.outer_inner1_nested3_b, subvec(test_value, 5, 2)),
                (dut.outer_inner1_nested3_c, subvec(test_value, 4, 2)),
                #
                (dut.outer_inner2_all, subvec(test_value, 15, 8)),
                (dut.outer_inner2_nested1_all, subvec(test_value, 11, 8)),
                (dut.outer_inner2_nested1_a, subvec(test_value, 8, 8)),
                (dut.outer_inner2_nested1_b, subvec(test_value, 11, 8)),
                (dut.outer_inner2_nested1_c, subvec(test_value, 10, 8)),
                #
                (dut.outer_inner2_nested2_all, subvec(test_value, 11, 8)),
                (dut.outer_inner2_nested2_a, subvec(test_value, 8, 8)),
                (dut.outer_inner2_nested2_b, subvec(test_value, 11, 8)),
                (dut.outer_inner2_nested2_c, subvec(test_value, 10, 8)),
                #
                (dut.outer_inner2_nested3_all, subvec(test_value, 13, 10)),
                (dut.outer_inner2_nested3_a, subvec(test_value, 10, 10)),
                (dut.outer_inner2_nested3_b, subvec(test_value, 13, 10)),
                (dut.outer_inner2_nested3_c, subvec(test_value, 12, 10)),
            ],
            check_msg=f"{test_value=}",
        )


class Unittest(unittest.TestCase):
    def test_bitfield(self):
        cohdl_testutil.run_cocotb_tests(test_bitfield, __file__, self.__module__)
