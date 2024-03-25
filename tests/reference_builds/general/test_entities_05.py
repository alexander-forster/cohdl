from __future__ import annotations

import unittest

import cohdl
from cohdl import Port, Bit
from cohdl import std

import itertools
from cohdl_testutil import cocotb_util


class BaseEntity(cohdl.Entity):
    base_a = Port.input(Bit)
    base_b = Port.input(Bit)

    base_result = Port.output(Bit)

    def architecture(self):
        @std.concurrent
        def logic():
            self.base_result <<= self.base_a | self.base_b


class DerivedEntity(BaseEntity):
    derived_a = Port.input(Bit)
    derived_b = Port.input(Bit)

    derived_result = Port.output(Bit)
    mixed_a = Port.output(Bit)
    mixed_b = Port.output(Bit)

    def architecture(self):
        super().architecture()

        @std.concurrent
        def logic():
            self.derived_result <<= self.derived_a & self.derived_b
            self.mixed_a <<= self.base_a | self.derived_a
            self.mixed_b <<= self.base_b ^ self.derived_b


class test_entities_05(cohdl.Entity):
    inp_a = Port.input(Bit)
    inp_b = Port.input(Bit)
    out_result = Port.output(Bit)

    inp_base_a = Port.input(Bit)
    inp_base_b = Port.input(Bit)
    out_base_result = Port.output(Bit)
    inp_derived_a = Port.input(Bit)
    inp_derived_b = Port.input(Bit)
    out_derived_result = Port.output(Bit)
    out_mixed_a = Port.output(Bit)
    out_mixed_b = Port.output(Bit)

    def architecture(self):
        BaseEntity(base_a=self.inp_a, base_b=self.inp_b, base_result=self.out_result)

        DerivedEntity(
            base_a=self.inp_base_a,
            base_b=self.inp_base_b,
            base_result=self.out_base_result,
            derived_a=self.inp_derived_a,
            derived_b=self.inp_derived_b,
            derived_result=self.out_derived_result,
            mixed_a=self.out_mixed_a,
            mixed_b=self.out_mixed_b,
        )


#
# test code
#


@cocotb_util.test()
async def testbench_entities_01(dut: test_entities_05):
    inp_gen = cocotb_util.ConstrainedGenerator(1)

    for inp_a, inp_b in itertools.product(inp_gen.all(), inp_gen.all()):
        for inp_base_a, inp_base_b in itertools.product(inp_gen.all(), inp_gen.all()):
            for inp_derived_a, inp_derived_b in itertools.product(
                inp_gen.all(), inp_gen.all()
            ):
                await cocotb_util.check_concurrent(
                    [
                        (dut.inp_a, inp_a),
                        (dut.inp_b, inp_b),
                        (dut.inp_base_a, inp_base_a),
                        (dut.inp_base_b, inp_base_b),
                        (dut.inp_derived_a, inp_derived_a),
                        (dut.inp_derived_b, inp_derived_b),
                    ],
                    [
                        (dut.out_result, inp_a | inp_b),
                        (dut.out_base_result, inp_base_a | inp_base_b),
                        (dut.out_derived_result, inp_derived_a & inp_derived_b),
                        (dut.out_mixed_a, inp_base_a | inp_derived_a),
                        (dut.out_mixed_b, inp_base_b ^ inp_derived_b),
                    ],
                )


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(
            test_entities_05,
            __file__,
            self.__module__,
            build_files=[
                "BaseEntity.vhd",
                "DerivedEntity.vhd",
            ],
        )
