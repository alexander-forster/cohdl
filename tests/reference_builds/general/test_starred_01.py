from __future__ import annotations


import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Signal, Unsigned, Signed, always
from cohdl import std

import itertools
from cohdl_testutil import cocotb_util
from cohdl_testutil.cocotb_mock import MockBase


class test_starred_01(cohdl.Entity):
    inp1 = Port.input(BitVector[4])
    inp2 = Port.input(BitVector[4])
    inp3 = Port.input(BitVector[4])
    inp4 = Port.input(BitVector[4])

    output1 = Port.output(BitVector[4])
    output2 = Port.output(BitVector[4])
    output3 = Port.output(BitVector[4])
    output4 = Port.output(BitVector[4])

    def architecture(self):
        inputs = [self.inp1, self.inp2, self.inp3, self.inp4]

        @std.concurrent
        def proc():
            a1, b1, c1, d1 = inputs
            a2, b2, *bc2 = inputs
            *ab3, c3, d3 = inputs
            a4, *bc4, d4 = inputs

            self.output1 <<= a1 & b1 & c1 & d1
            self.output2 <<= a2 | b2 | bc2[0] | bc2[1]
            self.output3 <<= ab3[0] ^ ab3[1] ^ c3 ^ d3
            self.output4 <<= a4 & bc4[0] | bc4[1] ^ d4


#
# test code
#


@cocotb_util.test()
async def testbench_always_01(dut: test_starred_01):
    gen = cocotb_util.ConstrainedGenerator

    for inp1, inp2, inp3, inp4 in itertools.product(
        gen(4).random(8),
        gen(4).random(8),
        gen(4).random(8),
        gen(4).random(8),
    ):
        await cocotb_util.check_concurrent(
            [
                (dut.inp1, inp1),
                (dut.inp2, inp2),
                (dut.inp3, inp3),
                (dut.inp4, inp4),
            ],
            [
                (dut.output1, inp1 & inp2 & inp3 & inp4),
                (dut.output2, inp1 | inp2 | inp3 | inp4),
                (dut.output3, inp1 ^ inp2 ^ inp3 ^ inp4),
                (dut.output4, inp1 & inp2 | inp3 ^ inp4),
            ],
        )


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_starred_01, __file__, self.__module__)
