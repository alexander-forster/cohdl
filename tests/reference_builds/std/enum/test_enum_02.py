from __future__ import annotations

import unittest

import cohdl
from cohdl import std, Bit, BitVector, Unsigned, Port, Null, Full

import cohdl_testutil
from cohdl_testutil.cocotb_util import ConstrainedGenerator

from cohdl_testutil import cocotb_util

import cocotb


class EnumA(std.Enum[BitVector[4]]):
    a = Null
    b = "0001"
    c = BitVector[4]("0010")


class EnumB(std.Enum[Unsigned[4]]):
    d = 3, "info unsigned"
    e = Full, "info Full"
    f = Unsigned[4](7)
    g = std.Enum("0110")


class Record(std.Record):
    enum_a: EnumA
    member_bit: Bit
    enum_b: EnumB


class test_enum_02(cohdl.Entity):
    inp_a = Port.input(BitVector[4])
    inp_bit = Port.input(Bit)
    inp_b = Port.input(BitVector[4])

    out_assigned_a = Port.output(BitVector[4])
    out_bit = Port.output(Bit)
    out_deserialized_b = Port.output(BitVector[4])

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
        rec_signal = std.Signal[Record]()

        @std.concurrent
        def logic():
            inp_a = EnumA._unsafe_init_(self.inp_a)
            inp_b = EnumB._unsafe_init_(self.inp_b)

            assert std.instance_check(inp_a.raw, BitVector[4])
            assert std.instance_check(inp_b.raw, Unsigned[4])
            assert std.count_bits(inp_a) == 4
            assert std.count_bits(inp_b) == 4
            assert std.count_bits(Record) == 9

            rec_signal.enum_a <<= inp_a
            rec_signal.member_bit <<= self.inp_bit
            rec_signal.enum_b <<= inp_b

            self.out_assigned_a <<= rec_signal.enum_a.raw

            self.is_a <<= inp_a == EnumA.a
            self.is_b <<= inp_a == EnumA.b
            self.is_c <<= inp_a == EnumA.c
            self.is_d <<= inp_b == EnumB.d
            self.is_e <<= inp_b == EnumB.e
            self.is_f <<= inp_b == EnumB.f
            self.is_g <<= inp_b == EnumB.g

            self.is_not_a <<= inp_a != EnumA.a
            self.is_not_b <<= inp_a != EnumA.b
            self.is_not_c <<= inp_a != EnumA.c
            self.is_not_d <<= inp_b != EnumB.d
            self.is_not_e <<= inp_b != EnumB.e
            self.is_not_f <<= inp_b != EnumB.f
            self.is_not_g <<= inp_b != EnumB.g

            serialized = std.to_bits(rec_signal)
            deserialized = std.from_bits[Record](serialized)
            self.out_deserialized_b <<= deserialized.enum_b.raw
            self.out_bit <<= deserialized.member_bit


@cocotb.test()
async def testbench_enum_02(dut: test_enum_02):
    dut.inp_a.value = 0
    dut.inp_bit.value = 0
    dut.inp_b.value = 0

    await cocotb_util.step()

    for inp_a in ConstrainedGenerator(4).all():
        for inp_b in ConstrainedGenerator(4).all():
            for inp_bit in ConstrainedGenerator(1).all():
                await cocotb_util.check_concurrent(
                    [
                        (dut.inp_a, inp_a),
                        (dut.inp_b, inp_b),
                        (dut.inp_bit, inp_bit),
                    ],
                    [
                        (dut.out_assigned_a, inp_a),
                        (dut.out_bit, inp_bit),
                        (dut.out_deserialized_b, inp_b),
                        (dut.is_a, inp_a == 0),
                        (dut.is_b, inp_a == 1),
                        (dut.is_c, inp_a == 2),
                        (dut.is_d, inp_b == 3),
                        (dut.is_e, inp_b == 15),
                        (dut.is_f, inp_b == 7),
                        (dut.is_g, inp_b == 6),
                        (dut.is_not_a, inp_a != 0),
                        (dut.is_not_b, inp_a != 1),
                        (dut.is_not_c, inp_a != 2),
                        (dut.is_not_d, inp_b != 3),
                        (dut.is_not_e, inp_b != 15),
                        (dut.is_not_f, inp_b != 7),
                        (dut.is_not_g, inp_b != 6),
                    ],
                )


class Unittest(unittest.TestCase):
    def test_enum_02(self):
        assert EnumA.a.info is None
        assert EnumA.b.info is None
        assert EnumA.c.info is None
        assert EnumB.d.info == "info unsigned"
        assert EnumB.e.info == "info Full"
        assert EnumB.f.info is None
        assert EnumB.g.info is None

        assert EnumA.a.name is "a"
        assert EnumA.b.name is "b"
        assert EnumA.c.name is "c"
        assert EnumB.d.name is "d"
        assert EnumB.e.name is "e"
        assert EnumB.f.name is "f"
        assert EnumB.g.name is "g"

        assert type(EnumA.a) is EnumA
        assert type(EnumA.b) is EnumA
        assert type(EnumA.c) is EnumA
        assert type(EnumB.d) is EnumB
        assert type(EnumB.e) is EnumB
        assert type(EnumB.f) is EnumB
        assert type(EnumB.g) is EnumB

        assert len(EnumA.__members__) == 3
        assert len(EnumB.__members__) == 4
        assert EnumA._default_ is EnumA.a
        assert EnumB._default_ is EnumB.d
        assert EnumA.__members__["a"] is EnumA.a
        assert EnumA.__members__["b"] is EnumA.b
        assert EnumA.__members__["c"] is EnumA.c
        assert EnumB.__members__["d"] is EnumB.d
        assert EnumB.__members__["e"] is EnumB.e
        assert EnumB.__members__["f"] is EnumB.f
        assert EnumB.__members__["g"] is EnumB.g

        cohdl_testutil.run_cocotb_tests(test_enum_02, __file__, self.__module__)
