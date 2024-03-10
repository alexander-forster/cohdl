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


class SelectorArg:
    T: type

    def __init__(self, T):
        self.T = T

    def __hash__(self) -> int:
        return hash(self.T)

    def __eq__(self, other: SelectorArg) -> bool:
        return self.T is other.T


class Selector(std.Record):
    select: Bit
    a: EnumA
    b: EnumA

    def get(self):
        return self.b if self.select else self.a


class test_enum_03(cohdl.Entity):
    inp_select = Port.input(Bit)
    inp_a = Port.input(BitVector[4])
    inp_b = Port.input(BitVector[4])

    result = Port.output(BitVector[4])

    def architecture(self):
        rec_signal = std.Signal[Selector]()

        @std.concurrent
        def logic():
            inp_a = EnumA._unsafe_init_(self.inp_a)
            inp_b = EnumA._unsafe_init_(self.inp_b)

            rec_signal.select <<= self.inp_select
            rec_signal.a <<= inp_a
            rec_signal.b <<= inp_b

            self.result <<= rec_signal.get().raw


@cocotb.test()
async def testbench_enum_03(dut: test_enum_03):
    dut.inp_select.value = 0
    dut.inp_a.value = 0
    dut.inp_b.value = 0

    await cocotb_util.step()

    for inp_a in ConstrainedGenerator(4).all():
        for inp_b in ConstrainedGenerator(4).all():
            for select in ConstrainedGenerator(1).all():
                await cocotb_util.check_concurrent(
                    [
                        (dut.inp_a, inp_a),
                        (dut.inp_b, inp_b),
                        (dut.inp_select, select),
                    ],
                    [
                        (dut.result, inp_b if select else inp_a),
                    ],
                )


class Unittest(unittest.TestCase):
    def test_enum_03(self):
        cohdl_testutil.run_cocotb_tests(test_enum_03, __file__, self.__module__)
