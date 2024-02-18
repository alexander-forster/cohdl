from __future__ import annotations

import unittest

import cohdl
from cohdl import std, Bit, BitVector, Port, Unsigned, Signed, Temporary

import cohdl_testutil
from cohdl_testutil.cocotb_util import ConstraindValue, ConstrainedGenerator

from cohdl_testutil import cocotb_util

import random
import cocotb


class WidthArg(int):
    pass


class Inner(std.Record[WidthArg]):
    a: Bit
    b: BitVector[WidthArg]
    c: Unsigned[WidthArg]
    d: Signed[WidthArg]

    def check_fields(self):
        width_arg = self._template_meta_.arg

        assert std.instance_check(self.a, Bit)
        assert std.instance_check(self.b, BitVector[width_arg])
        assert std.instance_check(self.c, Unsigned[width_arg])
        assert std.instance_check(self.d, Signed[width_arg])


class OuterRecord(std.Record[WidthArg]):
    inner_1: Inner[WidthArg]
    inner_2: Inner[8]
    bit: Bit
    vec: BitVector[WidthArg]

    def check_fields(self):
        width_arg = self._template_meta_.arg
        self.inner_1.check_fields()
        self.inner_2.check_fields()
        assert std.instance_check(self.bit, Bit)
        assert std.instance_check(self.vec, BitVector[width_arg])


class test_record_02(cohdl.Entity):
    input = Port.input(BitVector[64])

    out_4_inner1_a = Port.output(Bit)
    out_4_inner1_b = Port.output(BitVector[4])
    out_4_inner1_c = Port.output(Unsigned[4])
    out_4_inner1_d = Port.output(Signed[4])
    out_4_inner2_a = Port.output(Bit)
    out_4_inner2_b = Port.output(BitVector[8])
    out_4_inner2_c = Port.output(Unsigned[8])
    out_4_inner2_d = Port.output(Signed[8])
    out_4_bit = Port.output(Bit)
    out_4_vec = Port.output(BitVector[4])

    out_2_inner1_a = Port.output(Bit)
    out_2_inner1_b = Port.output(BitVector[2])
    out_2_inner1_c = Port.output(Unsigned[2])
    out_2_inner1_d = Port.output(Signed[2])
    out_2_inner2_a = Port.output(Bit)
    out_2_inner2_b = Port.output(BitVector[8])
    out_2_inner2_c = Port.output(Unsigned[8])
    out_2_inner2_d = Port.output(Signed[8])
    out_2_bit = Port.output(Bit)
    out_2_vec = Port.output(BitVector[2])

    def architecture(self):
        @std.concurrent
        def logic():
            inp_4 = OuterRecord[4](
                inner_1=Inner[4](
                    a=self.input[0],
                    b=self.input[4:1],
                    c=self.input[8:5],
                    d=self.input[12:9],
                ),
                inner_2=Inner[8](
                    a=self.input[13],
                    b=self.input[21:14],
                    c=self.input[29:22],
                    d=self.input[37:30],
                ),
                bit=self.input[38],
                vec=self.input[42:39],
            )

            inp_4.check_fields()

            self.out_4_inner1_a <<= inp_4.inner_1.a
            self.out_4_inner1_b <<= inp_4.inner_1.b
            self.out_4_inner1_c <<= inp_4.inner_1.c
            self.out_4_inner1_d <<= inp_4.inner_1.d
            self.out_4_inner2_a <<= inp_4.inner_2.a
            self.out_4_inner2_b <<= inp_4.inner_2.b
            self.out_4_inner2_c <<= inp_4.inner_2.c
            self.out_4_inner2_d <<= inp_4.inner_2.d
            self.out_4_bit <<= inp_4.bit
            self.out_4_vec <<= inp_4.vec

        sig_2 = std.Signal[OuterRecord[2]]()
        sig_2.check_fields()

        @std.concurrent
        def logic_2():
            inp_2 = OuterRecord[2](
                inner_1=Inner[2](
                    a=self.input[0],
                    b=self.input[2:1],
                    c=self.input[4:3],
                    d=self.input[6:5],
                ),
                inner_2=Inner[8](
                    a=self.input[13],
                    b=self.input[21:14],
                    c=self.input[29:22],
                    d=self.input[37:30],
                ),
                bit=self.input[38],
                vec=self.input[40:39],
            )

            sig_2.next = inp_2

            serialized = std.to_bits(sig_2)
            deserialized = std.from_bits[OuterRecord[2]](serialized, std.Signal)

            deserialized.check_fields()

            self.out_2_inner1_a <<= deserialized.inner_1.a
            self.out_2_inner1_b <<= deserialized.inner_1.b
            self.out_2_inner1_c <<= deserialized.inner_1.c
            self.out_2_inner1_d <<= deserialized.inner_1.d
            self.out_2_inner2_a <<= deserialized.inner_2.a
            self.out_2_inner2_b <<= deserialized.inner_2.b
            self.out_2_inner2_c <<= deserialized.inner_2.c
            self.out_2_inner2_d <<= deserialized.inner_2.d
            self.out_2_bit <<= deserialized.bit
            self.out_2_vec <<= deserialized.vec


@cocotb.test()
async def testbench_record_02(dut: test_record_02):
    for input in ConstrainedGenerator(64).random(64):
        await cocotb_util.check_concurrent(
            [
                (dut.input, input),
            ],
            [
                (dut.out_4_inner1_a, input.get_slice(0, 0)),
                (dut.out_4_inner1_b, input.get_slice(1, 4)),
                (dut.out_4_inner1_c, input.get_slice(5, 8)),
                (dut.out_4_inner1_d, input.get_slice(9, 12)),
                (dut.out_4_inner2_a, input.get_slice(13, 13)),
                (dut.out_4_inner2_b, input.get_slice(14, 21)),
                (dut.out_4_inner2_c, input.get_slice(22, 29)),
                (dut.out_4_inner2_d, input.get_slice(30, 37)),
                (dut.out_4_bit, input.get_slice(38, 38)),
                (dut.out_4_vec, input.get_slice(39, 42)),
                #
                (dut.out_2_inner1_a, input.get_slice(0, 0)),
                (dut.out_2_inner1_b, input.get_slice(1, 2)),
                (dut.out_2_inner1_c, input.get_slice(3, 4)),
                (dut.out_2_inner1_d, input.get_slice(5, 6)),
                (dut.out_2_inner2_a, input.get_slice(13, 13)),
                (dut.out_2_inner2_b, input.get_slice(14, 21)),
                (dut.out_2_inner2_c, input.get_slice(22, 29)),
                (dut.out_2_inner2_d, input.get_slice(30, 37)),
                (dut.out_2_bit, input.get_slice(38, 38)),
                (dut.out_2_vec, input.get_slice(39, 40)),
            ],
        )


class Unittest(unittest.TestCase):
    def test_record_02(self):
        cohdl_testutil.run_cocotb_tests(test_record_02, __file__, self.__module__)
