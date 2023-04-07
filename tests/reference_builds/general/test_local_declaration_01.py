from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Signal, Unsigned, Signed
from cohdl import std

import itertools
from cohdl_testutil import cocotb_util


class test_local_declaration_01(cohdl.Entity):
    inp1 = Port.input(Bit)
    inp2 = Port.input(BitVector[4])
    inp3 = Port.input(Unsigned[4])
    inp4 = Port.input(Signed[4])

    out1 = Port.output(Bit)
    out2 = Port.output(BitVector[4])
    out3 = Port.output(Unsigned[4])
    out4 = Port.output(Signed[4])

    def architecture(self):
        @std.concurrent
        def logic():
            a = Signal[Bit]()
            b = Signal[BitVector[4]]()
            c = Signal[Unsigned[4]]()
            d = Signal[Signed[4]]()

            a <<= self.inp1
            b <<= self.inp2
            c <<= self.inp3
            d <<= self.inp4

            self.out1 <<= a
            self.out2 <<= b
            self.out3 <<= c
            self.out4 <<= d


#
# test code
#


@cocotb_util.test()
async def testbench_local_declaration_01(dut: test_local_declaration_01):
    gen = cocotb_util.ConstrainedGenerator

    for inp1, inp2, inp3, inp4 in itertools.product(
        gen(1).all(),
        gen(4).all(),
        gen(4).all(),
        gen(4).all(),
    ):
        await cocotb_util.check_concurrent(
            [
                (dut.inp1, inp1),
                (dut.inp2, inp2),
                (dut.inp3, inp3),
                (dut.inp4, inp4),
            ],
            [
                (dut.out1, inp1),
                (dut.out2, inp2),
                (dut.out3, inp3),
                (dut.out4, inp4),
            ],
        )


class Unittest(unittest.TestCase):
    def test_local_declaration_01(self):
        cocotb_util.run_cocotb_tests(
            test_local_declaration_01, __file__, self.__module__
        )
