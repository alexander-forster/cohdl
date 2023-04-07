from __future__ import annotations

import unittest

import cohdl
from cohdl import BitVector, Port, Bit
from cohdl import std

import itertools
from cohdl_testutil import cocotb_util


class OrEntity(cohdl.Entity):
    a = Port.input(Bit)
    b = Port.input(Bit)

    result = Port.output(Bit)

    def architecture(self):
        @std.concurrent
        def logic():
            self.result <<= self.a | self.b


class AndEntity(cohdl.Entity):
    a = Port.input(Bit)
    b = Port.input(Bit)

    result = Port.output(Bit)

    def architecture(self):
        @std.concurrent
        def logic():
            self.result <<= self.a & self.b


class XorEntity(cohdl.Entity):
    a = Port.input(Bit)
    b = Port.input(Bit)

    result = Port.output(Bit)

    def architecture(self):
        @std.concurrent
        def logic():
            self.result <<= self.a ^ self.b


class NestedXorEntity(cohdl.Entity):
    a = Port.input(Bit)
    b = Port.input(Bit)

    result = Port.output(Bit)

    def architecture(self):
        XorEntity(a=self.a, b=self.b, result=self.result)


class test_entities_04(cohdl.Entity):
    a = Port.input(Bit)
    b = Port.input(Bit)
    c = Port.input(Bit)

    result_and = Port.output(Bit)
    result_and_2 = Port.output(Bit)
    result_or = Port.output(Bit)
    result_or_2 = Port.output(Bit)
    result_xor = Port.output(Bit)
    result_xor_2 = Port.output(Bit)

    def architecture(self):
        OrEntity(a=self.a, b=self.b, result=self.result_or)
        OrEntity(a=self.a, b=self.b, result=self.result_or_2)
        AndEntity(a=self.a, b=self.b, result=self.result_and)
        AndEntity(a=self.a, b=self.c, result=self.result_and_2)
        NestedXorEntity(a=self.a, b=self.b, result=self.result_xor)
        NestedXorEntity(a=self.b, b=self.c, result=self.result_xor_2)


#
# test code
#


@cocotb_util.test()
async def testbench_entities_01(dut: test_entities_04):
    inp_gen = cocotb_util.ConstrainedGenerator(1)

    for a, b, c in itertools.product(inp_gen.all(), inp_gen.all(), inp_gen.all()):
        await cocotb_util.check_concurrent(
            [(dut.a, a), (dut.b, b), (dut.c, c)],
            [
                (dut.result_or, a | b, "or"),
                (dut.result_or_2, a | b, "or2"),
                (dut.result_and, a & b, "and"),
                (dut.result_and_2, a & c, "and2"),
                (dut.result_xor, a ^ b, "xor"),
                (dut.result_xor_2, b ^ c, "xor2"),
            ],
        )


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(
            test_entities_04,
            __file__,
            self.__module__,
            build_files=[
                "OrEntity.vhd",
                "AndEntity.vhd",
                "NestedXorEntity.vhd",
                "XorEntity.vhd",
            ],
        )
