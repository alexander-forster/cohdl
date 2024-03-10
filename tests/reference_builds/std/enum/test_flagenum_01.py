from __future__ import annotations

import unittest
import random

import cohdl
from cohdl import std, Bit, BitVector, Unsigned, Port

from cohdl.std import enum

import cohdl_testutil
from cohdl_testutil import cocotb_util

import cocotb


class SimpleEnum(enum.FlagEnum[Unsigned[8]]):
    a = std.Enum(1 << 0, "bit 0")
    b = std.Enum(1 << 1, "bit 1")
    c = 1 << 4, "bit 4"


class test_flagenum_01(cohdl.Entity):
    inp_a = Port.input(BitVector[8])
    inp_b = Port.input(BitVector[8])

    out_and = Port.output(BitVector[8])
    out_or = Port.output(BitVector[8])
    out_xor = Port.output(BitVector[8])

    has_a = Port.output(Bit)
    has_b = Port.output(Bit)
    has_c = Port.output(Bit)

    is_a = Port.output(Bit)
    is_b = Port.output(Bit)
    is_c = Port.output(Bit)

    def architecture(self):
        enum_a = std.Signal[SimpleEnum]()

        @std.concurrent
        def logic():
            enum_a.raw <<= self.inp_a
            enum_b = SimpleEnum._unsafe_init_(self.inp_b)

            self.out_and <<= (enum_a & enum_b).raw
            self.out_or <<= (enum_a | enum_b).raw
            self.out_xor <<= (enum_a ^ enum_b).raw

            self.has_a <<= bool(enum_a & SimpleEnum.a)
            self.has_b <<= bool(enum_a & SimpleEnum.b)
            self.has_c <<= bool(enum_a & SimpleEnum.c)

            self.is_a <<= enum_a == SimpleEnum.a
            self.is_b <<= enum_a == SimpleEnum.b
            self.is_c <<= enum_a == SimpleEnum.c


@cocotb.test()
async def testbench_flagenum_01(dut: test_flagenum_01):

    for _ in range(64):
        inp_a = random.randint(0, 255)
        inp_b = random.randint(0, 255)

        await cocotb_util.check_concurrent(
            [
                (dut.inp_a, inp_a),
                (dut.inp_b, inp_b),
            ],
            [
                (dut.out_and, inp_a & inp_b),
                (dut.out_or, inp_a | inp_b),
                (dut.out_xor, inp_a ^ inp_b),
                (dut.has_a, bool(inp_a & (1 << 0))),
                (dut.has_b, bool(inp_a & (1 << 1))),
                (dut.has_c, bool(inp_a & (1 << 4))),
                (dut.is_a, inp_a == 1 << 0),
                (dut.is_b, inp_a == 1 << 1),
                (dut.is_c, inp_a == 1 << 4),
            ],
        )


class Unittest(unittest.TestCase):
    def test_flagenum_01(self):
        assert SimpleEnum.a.info == "bit 0"
        assert SimpleEnum.b.info == "bit 1"
        assert SimpleEnum.c.info == "bit 4"

        assert SimpleEnum.a.name == "a"
        assert SimpleEnum.b.name == "b"
        assert SimpleEnum.c.name == "c"

        assert SimpleEnum._underlying_ is Unsigned[8]
        assert SimpleEnum._default_.raw == Unsigned[8](1)

        cohdl_testutil.run_cocotb_tests(test_flagenum_01, __file__, self.__module__)
