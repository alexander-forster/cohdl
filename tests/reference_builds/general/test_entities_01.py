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


class test_entities_01(cohdl.Entity):
    a = Port.input(Bit)
    b = Port.input(Bit)
    result = Port.output(Bit)

    def architecture(self):
        OrEntity(a=self.a, b=self.b, result=self.result)


#
# test code
#


@cocotb_util.test()
async def testbench_entities_01(dut: test_entities_01):
    inp_gen = cocotb_util.ConstrainedGenerator(1)

    for a, b in itertools.product(inp_gen.all(), inp_gen.all()):
        await cocotb_util.check_concurrent(
            [(dut.a, a), (dut.b, b)],
            [
                (dut.result, a | b),
            ],
        )


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(
            test_entities_01, __file__, self.__module__, build_files=["OrEntity.vhd"]
        )
