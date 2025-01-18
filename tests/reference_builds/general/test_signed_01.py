from __future__ import annotations

import unittest

import cohdl
from cohdl import (
    BitVector,
    Port,
    Signal,
    Unsigned,
    Signed,
    Array,
)

from cohdl import std
from cohdl import op
from cohdl_testutil import cocotb_util


class test_operations(cohdl.Entity):
    if True:
        sw = Port.input(BitVector[4])

        a = Port.input(Signed[4])
        b = Port.input(Signed[4])

        # b used for divisions (never zero)
        b_div = Port.input(Signed[4])

        op_add = Port.output(Signed[4])
        op_sub = Port.output(Signed[4])
        op_mul = Port.output(Signed[8])
        op_div = Port.output(Signed[4])
        op_mod = Port.output(Signed[4])

        cast_a = Port.output(BitVector[4])
        cast_b = Port.output(BitVector[4])
        cast_c = Port.output(BitVector[5])
        cast_e = Port.output(Unsigned[4])
        cast_f = Port.output(Signed[4])
        cast_g = Port.output(Unsigned[4])
        cast_h = Port.output(Signed[4])

        array_inp = Port.input(BitVector[4])
        array_out = Port.output(BitVector[4])
        array_index = Port.input(BitVector[4])

        slice_s_a = Port.output(BitVector[3])
        slice_s_b = Port.output(BitVector[3])
        slice_s_c = Port.output(BitVector[3])
        slice_s_d = Port.output(BitVector[3])

        init_from_same = Port.output(Signed[4])
        init_from_shorter = Port.output(Signed[5])
        init_from_shorter2 = Port.output(Signed[6])

        init_from_unsigned1 = Port.output(Signed[5])
        init_from_unsigned2 = Port.output(Signed[6])
        init_from_unsigned3 = Port.output(Signed[7])

        choose_shorter1 = Port.output(Signed[5])
        choose_shorter2 = Port.output(Signed[6])
        choose_shorter3 = Port.output(Signed[7])

        choose_unsigned = Port.output(Signed[6])

    def architecture(self):
        array = Signal[Array[BitVector[4], 8]]()

        @std.concurrent
        def logic_simple():
            self.op_add <<= self.a + self.b
            self.op_sub <<= self.a - self.b
            self.op_mul <<= self.a * self.b
            self.op_div <<= op.truncdiv(self.a, self.b_div)
            self.op_mod <<= self.a % self.b_div

            self.cast_a.signed <<= self.a
            self.cast_b.signed <<= 6
            self.cast_c.signed <<= self.a
            self.cast_e <<= self.sw.unsigned
            self.cast_f <<= self.sw.signed
            self.cast_g <<= self.sw
            self.cast_h <<= self.sw

            array[self.array_index.signed] <<= self.array_inp
            self.array_out <<= array[self.array_index.signed]

        @std.concurrent
        def logic_slices():
            self.slice_s_a <<= self.b[2:0]
            self.slice_s_b <<= self.b.lsb(3)
            self.slice_s_c <<= self.b[3:1]
            self.slice_s_d <<= self.b.msb(3)

        @std.concurrent
        def logic_init():
            self.init_from_same <<= Signal[Signed[4]](self.a)
            self.init_from_shorter <<= Signal[Signed[5]](self.a)
            self.init_from_shorter2 <<= Signal[Signed[6]](self.a)

            self.init_from_unsigned1 <<= Signal[Signed[5]](self.a.unsigned)
            self.init_from_unsigned2 <<= Signal[Signed[6]](self.a.unsigned)
            self.init_from_unsigned3 <<= Signal[Signed[7]](self.a.unsigned)

            self.choose_shorter1 <<= self.a if self.a < self.b else self.b
            self.choose_shorter2 <<= (
                self.init_from_shorter if self.a < self.b else self.b
            )
            self.choose_shorter3 <<= (
                self.b if self.a < self.b else self.init_from_shorter2
            )

            self.choose_unsigned <<= self.a if self.a < self.b else self.b.unsigned


#
# test code
#


def as_signed(inp):
    if inp >= 8:
        return as_signed(inp - 16)
    if inp < -8:
        return as_signed(inp + 16)
    return inp


@cocotb_util.test()
async def testbench_operations(dut: test_operations):
    for a in range(16):
        for b in range(16):
            sa = as_signed(a)
            sb = as_signed(b)

            b_div = as_signed(b if b != 0 else 1)

            op_add = as_signed(a + b)
            op_sub = as_signed(a - b)
            op_mul = as_signed(a) * as_signed(b)

            op_div = int(as_signed(a) / as_signed(b_div))
            op_mod = as_signed(a) % as_signed(b_div)

            b_lower = as_signed(b) & 0b111
            b_upper = b >> 1

            await cocotb_util.check_concurrent(
                [
                    (dut.sw, a),
                    (dut.a, a),
                    (dut.b, b),
                    (dut.b_div, b_div),
                    (dut.array_index, abs(as_signed(a)) // 2),
                    (dut.array_inp, b),
                ],
                [
                    (dut.op_add, op_add, "ADD"),
                    (dut.op_sub, op_sub, "SUB"),
                    (dut.op_mul, op_mul, "MUL"),
                    (dut.op_div, op_div, "DIV"),
                    (dut.op_mod, op_mod, "MOD"),
                    (dut.cast_a, as_signed(a), "cast_a"),
                    (dut.cast_b, 6, "cast_b"),
                    (dut.cast_c, as_signed(a), "cast_c"),
                    # (dut.cast_d, 7, "cast_d"),
                    (dut.cast_e, a, "cast_e"),
                    (dut.cast_f, as_signed(a), "cast_f"),
                    (dut.cast_g, a, "cast_g"),
                    (dut.cast_h, as_signed(a), "cast_h"),
                    (dut.array_out, b, "array_out"),
                    (dut.slice_s_a, b_lower, "slice_s_a"),
                    (dut.slice_s_b, b_lower, "slice_s_b"),
                    (dut.slice_s_c, b_upper, "slice_s_c"),
                    (dut.slice_s_d, b_upper, "slice_s_d"),
                    (dut.init_from_same, as_signed(a), "init_from_same"),
                    (dut.init_from_shorter, as_signed(a), "init_from_shorter"),
                    (dut.init_from_shorter2, as_signed(a), "init_from_shorter2"),
                    (dut.init_from_unsigned1, a, "init_from_unsigned1"),
                    (dut.init_from_unsigned2, a, "init_from_unsigned2"),
                    (dut.init_from_unsigned3, a, "init_from_unsigned3"),
                    (dut.choose_shorter1, sa if sa < sb else sb, "choose_shorter1"),
                    (dut.choose_shorter2, sa if sa < sb else sb, "choose_shorter2"),
                    (dut.choose_shorter3, sb if sa < sb else sa, "choose_shorter3"),
                    (dut.choose_unsigned, sa if sa < sb else b, "choose_unsigned"),
                ],
                check_msg=f"{a=}, {b=}, {b_div=}, {as_signed(b_div)=}",
            )


class Unittest(unittest.TestCase):
    def test_operations(self):
        cocotb_util.run_cocotb_tests(test_operations, __file__, self.__module__)
