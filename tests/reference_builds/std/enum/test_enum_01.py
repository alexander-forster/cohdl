from __future__ import annotations

import unittest

import cohdl
from cohdl import std, Bit, BitVector, Port, Null, Full

from cohdl.std import enum

import cohdl_testutil
from cohdl_testutil.cocotb_util import ConstrainedGenerator

from cohdl_testutil import cocotb_util

import cocotb


class SimpleEnum(enum.Enum[BitVector[4]]):
    a = Null
    b = "0001"
    c = BitVector[4]("0010")
    d = std.as_bitvector("0011"), "info bitvector"
    e = Full, "info Full"
    f = enum.Enum("1001")
    g = enum.Enum("0110")


class test_enum_01(cohdl.Entity):
    inp_unsafe = Port.input(BitVector[4])
    out_assigned = Port.output(BitVector[4])
    out_deserialized = Port.output(BitVector[4])

    is_a = Port.output(Bit)
    is_b = Port.output(Bit)
    is_c = Port.output(Bit)
    is_d = Port.output(Bit)
    is_e = Port.output(Bit)
    is_f = Port.output(Bit)
    is_g = Port.output(Bit)

    is_not_a = Port.output(Bit)
    is_not_b = Port.output(Bit)
    is_not_c = Port.output(Bit)
    is_not_d = Port.output(Bit)
    is_not_e = Port.output(Bit)
    is_not_f = Port.output(Bit)
    is_not_g = Port.output(Bit)

    def architecture(self):
        enum_signal = std.Signal[SimpleEnum]()

        @std.concurrent
        def logic():
            input = SimpleEnum._unsafe_init_(self.inp_unsafe)

            enum_signal.next = input

            self.out_assigned <<= enum_signal.raw

            self.is_a <<= input == SimpleEnum.a
            self.is_b <<= input == SimpleEnum.b
            self.is_c <<= input == SimpleEnum.c
            self.is_d <<= input == SimpleEnum.d
            self.is_e <<= input == SimpleEnum.e
            self.is_f <<= input == SimpleEnum.f
            self.is_g <<= input == SimpleEnum.g

            self.is_not_a <<= input != SimpleEnum.a
            self.is_not_b <<= input != SimpleEnum.b
            self.is_not_c <<= input != SimpleEnum.c
            self.is_not_d <<= input != SimpleEnum.d
            self.is_not_e <<= input != SimpleEnum.e
            self.is_not_f <<= input != SimpleEnum.f
            self.is_not_g <<= input != SimpleEnum.g

            serialized = std.to_bits(input)
            self.out_deserialized <<= std.from_bits[SimpleEnum](serialized).raw


@cocotb.test()
async def testbench_enum_01(dut: test_enum_01):

    for inp in ConstrainedGenerator(4).all():
        await cocotb_util.check_concurrent(
            [
                (dut.inp_unsafe, inp),
            ],
            [
                (dut.out_assigned, inp),
                (dut.out_deserialized, inp),
                (dut.is_a, inp == 0),
                (dut.is_b, inp == 1),
                (dut.is_c, inp == 2),
                (dut.is_d, inp == 3),
                (dut.is_e, inp == 15),
                (dut.is_f, inp == 9),
                (dut.is_g, inp == 6),
                (dut.is_not_a, inp != 0),
                (dut.is_not_b, inp != 1),
                (dut.is_not_c, inp != 2),
                (dut.is_not_d, inp != 3),
                (dut.is_not_e, inp != 15),
                (dut.is_not_f, inp != 9),
                (dut.is_not_g, inp != 6),
            ],
        )


class Unittest(unittest.TestCase):
    def test_enum_01(self):
        assert SimpleEnum.a.info is None
        assert SimpleEnum.b.info is None
        assert SimpleEnum.c.info is None
        assert SimpleEnum.d.info == "info bitvector"
        assert SimpleEnum.e.info == "info Full"
        assert SimpleEnum.f.info is None
        assert SimpleEnum.g.info is None

        assert SimpleEnum.a.name is "a"
        assert SimpleEnum.b.name is "b"
        assert SimpleEnum.c.name is "c"
        assert SimpleEnum.d.name is "d"
        assert SimpleEnum.e.name is "e"
        assert SimpleEnum.f.name is "f"
        assert SimpleEnum.g.name is "g"

        assert type(SimpleEnum.a) is SimpleEnum
        assert type(SimpleEnum.b) is SimpleEnum
        assert type(SimpleEnum.c) is SimpleEnum
        assert type(SimpleEnum.d) is SimpleEnum
        assert type(SimpleEnum.e) is SimpleEnum
        assert type(SimpleEnum.f) is SimpleEnum
        assert type(SimpleEnum.g) is SimpleEnum

        assert len(SimpleEnum.__members__) == 7
        assert SimpleEnum._default_ is SimpleEnum.a
        assert SimpleEnum.__members__["a"] is SimpleEnum.a
        assert SimpleEnum.__members__["b"] is SimpleEnum.b
        assert SimpleEnum.__members__["c"] is SimpleEnum.c
        assert SimpleEnum.__members__["d"] is SimpleEnum.d
        assert SimpleEnum.__members__["e"] is SimpleEnum.e
        assert SimpleEnum.__members__["f"] is SimpleEnum.f
        assert SimpleEnum.__members__["g"] is SimpleEnum.g

        cohdl_testutil.run_cocotb_tests(test_enum_01, __file__, self.__module__)
