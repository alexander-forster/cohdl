from __future__ import annotations

import unittest

import cohdl
from cohdl import (
    Bit,
    BitVector,
    Port,
    Signal,
    Unsigned,
    Signed,
    select_with,
    Null,
    Full,
    enum,
    Array,
)

from cohdl import std
from cohdl_testutil import cocotb_util


class test_operations(cohdl.Entity):
    if True:
        sw = Port.input(BitVector[4])

        a = Port.input(Unsigned[4])
        b = Port.input(Unsigned[4])

        # b used for divisions (never zero)
        b_div = Port.input(Unsigned[4])

        op_add = Port.output(Unsigned[4])
        op_sub = Port.output(Unsigned[4])
        op_mul = Port.output(Unsigned[8])
        op_div = Port.output(Unsigned[4])
        op_mod = Port.output(Unsigned[4])

        cast_a = Port.output(BitVector[4])
        cast_b = Port.output(BitVector[4])
        cast_c = Port.output(BitVector[5])
        cast_d = Port.output(BitVector[4])
        cast_e = Port.output(Unsigned[4])
        cast_f = Port.output(Signed[4])
        cast_g = Port.output(Unsigned[4])
        cast_h = Port.output(Signed[4])

        array_inp = Port.input(BitVector[4])
        array_out = Port.output(BitVector[4])
        array_index = Port.input(BitVector[4])

        slice_sw_a = Port.output(BitVector[3])
        slice_sw_b = Port.output(BitVector[3])
        slice_sw_c = Port.output(BitVector[3])
        slice_sw_d = Port.output(BitVector[3])

        slice_u_a = Port.output(BitVector[3])
        slice_u_b = Port.output(BitVector[3])
        slice_u_c = Port.output(BitVector[3])
        slice_u_d = Port.output(BitVector[3])

        init_from_same = Port.output(Unsigned[4])
        init_from_shorter = Port.output(Unsigned[5])
        init_from_shorter2 = Port.output(Unsigned[6])

        choose_shorter1 = Port.output(Unsigned[5])
        choose_shorter2 = Port.output(Unsigned[6])
        choose_shorter3 = Port.output(Unsigned[7])

    def architecture(self):
        array = Signal[Array[BitVector[4], 16]]()

        @std.concurrent
        def logic_simple():

            self.op_add <<= self.a + self.b
            self.op_sub <<= self.a - self.b
            self.op_mul <<= self.a * self.b
            self.op_div <<= self.a // self.b_div
            self.op_mod <<= self.a % self.b_div

            self.cast_a.unsigned <<= self.a
            self.cast_b.unsigned <<= 12
            self.cast_c.signed <<= self.a
            self.cast_d.signed <<= 7
            self.cast_e <<= self.sw.unsigned
            self.cast_f <<= self.sw.signed
            self.cast_g <<= self.sw
            self.cast_h <<= self.sw

            array[self.array_index.unsigned] <<= self.array_inp
            self.array_out <<= array[self.array_index.unsigned]

        @std.concurrent
        def logic_slices():
            self.slice_sw_a <<= self.sw[2:0]
            self.slice_sw_b <<= self.sw.lsb(3)
            self.slice_sw_c <<= self.sw[3:1]
            self.slice_sw_d <<= self.sw.msb(3)

            self.slice_u_a <<= self.b[2:0]
            self.slice_u_b <<= self.b.lsb(3)
            self.slice_u_c <<= self.b[3:1]
            self.slice_u_d <<= self.b.msb(3)

        @std.concurrent
        def logic_init():
            self.init_from_same <<= Signal[Unsigned[4]](self.a)
            self.init_from_shorter <<= Signal[Unsigned[5]](self.a)
            self.init_from_shorter2 <<= Signal[Unsigned[6]](self.a)

            self.choose_shorter1 <<= self.a if self.a < self.b else self.b
            self.choose_shorter2 <<= (
                self.init_from_shorter if self.a < self.b else self.b
            )
            self.choose_shorter3 <<= (
                self.b if self.a < self.b else self.init_from_shorter2
            )


#
# test code
#


@cocotb_util.test()
async def testbench_operations(dut: test_operations):
    for a in range(16):
        for b in range(16):
            b_div = b if b != 0 else 1

            op_add = (a + b) % 16
            op_sub = (a - b + 16) % 16
            op_mul = a * b

            op_div = a // b_div
            op_mod = a % b_div

            b_lower = b & 0b111
            b_upper = b >> 1

            sw_lower = a & 0b111
            sw_upper = a >> 1

            await cocotb_util.check_concurrent(
                [
                    (dut.sw, a),
                    (dut.a, a),
                    (dut.b, b),
                    (dut.b_div, b_div),
                    (dut.array_index, a),
                    (dut.array_inp, b),
                ],
                [
                    (dut.op_add, op_add, "ADD"),
                    (dut.op_sub, op_sub, "SUB"),
                    (dut.op_mul, op_mul, "MUL"),
                    (dut.op_div, op_div, "DIV"),
                    (dut.op_mod, op_mod, "MOD"),
                    (dut.cast_a, a, "cast_a"),
                    (dut.cast_b, 12, "cast_b"),
                    (dut.cast_c, a, "cast_c"),
                    (dut.cast_d, 7, "cast_d"),
                    (dut.cast_e, a, "cast_e"),
                    (dut.cast_f, (a if a < 8 else (a - 16)), "cast_f"),
                    (dut.cast_g, a, "cast_g"),
                    (dut.cast_h, (a if a < 8 else (a - 16)), "cast_h"),
                    (dut.array_out, b, "array_out"),
                    (dut.slice_sw_a, sw_lower, "slice_sw_a"),
                    (dut.slice_sw_b, sw_lower, "slice_sw_b"),
                    (dut.slice_sw_c, sw_upper, "slice_sw_c"),
                    (dut.slice_sw_d, sw_upper, "slice_sw_d"),
                    (dut.slice_u_a, b_lower, "slice_u_a"),
                    (dut.slice_u_b, b_lower, "slice_u_b"),
                    (dut.slice_u_c, b_upper, "slice_u_c"),
                    (dut.slice_u_d, b_upper, "slice_u_d"),
                    (dut.init_from_same, a, "init_from_same"),
                    (dut.init_from_shorter, a, "init_from_shorter"),
                    (dut.init_from_shorter2, a, "init_from_shorter2"),
                    (dut.choose_shorter1, (a if a < b else b), "choose_shorter1"),
                    (dut.choose_shorter2, (a if a < b else b), "choose_shorter2"),
                    (dut.choose_shorter3, (b if a < b else a), "choose_shorter3"),
                ],
                check_msg=f"{a=}, {b=}",
            )


class Unittest(unittest.TestCase):
    def test_operations(self):
        cocotb_util.run_cocotb_tests(test_operations, __file__, self.__module__)
