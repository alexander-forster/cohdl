from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port
from cohdl import std

from cohdl_testutil import cocotb_util


class test_slice_02(cohdl.Entity):
    inp1 = Port.input(BitVector[5])

    out1_a = Port.output(BitVector[1])
    out1_b = Port.output(BitVector[2])
    out1_c = Port.output(BitVector[2])
    out1_d = Port.output(BitVector[7])
    out1_e = Port.output(BitVector[5])

    out2_a = Port.output(BitVector[1])
    out2_b = Port.output(BitVector[2])
    out2_c = Port.output(BitVector[2])
    out2_d = Port.output(BitVector[7])
    out2_e = Port.output(BitVector[5])

    def architecture(self):
        @std.concurrent
        def logic():
            self.out1_a <<= self.inp1[2,]
            self.out1_b <<= self.inp1[1, 4]
            self.out1_c <<= self.inp1[1:0,]
            self.out1_d <<= self.inp1[0, 0, 2:0, 4, 1]
            self.out1_e <<= self.inp1[4, 3, 2, 1, 0]

        @std.sequential
        def proc():
            inp = cohdl.Variable(self.inp1)
            self.out2_a <<= inp[2,]
            self.out2_b <<= inp[1, 4]
            self.out2_c <<= inp[1:0,]
            self.out2_d <<= inp[0, 0, 2:0, 4, 1]
            self.out2_e <<= inp[4, 3, 2, 1, 0]


#
# test code
#


@cocotb_util.test()
async def testbench_match_simple(dut: test_slice_02):
    inp_1_gen = cocotb_util.ConstrainedGenerator(5)

    for inp1 in inp_1_gen.all():
        await cocotb_util.check_concurrent(
            [
                (dut.inp1, inp1),
            ],
            [
                (dut.out1_a, inp1.get_bit(2)),
                (dut.out1_b, inp1.get_bit(1) @ inp1.get_bit(4)),
                (dut.out1_c, inp1.get_slice(0, 1)),
                (
                    dut.out1_d,
                    inp1.get_bit(0)
                    @ inp1.get_bit(0)
                    @ inp1.get_slice(0, 2)
                    @ inp1.get_bit(4)
                    @ inp1.get_bit(1),
                ),
                (
                    dut.out1_e,
                    inp1.get_bit(4)
                    @ inp1.get_bit(3)
                    @ inp1.get_bit(2)
                    @ inp1.get_bit(1)
                    @ inp1.get_bit(0),
                ),
                #
                #
                #
                (dut.out2_a, inp1.get_bit(2)),
                (dut.out2_b, inp1.get_bit(1) @ inp1.get_bit(4)),
                (dut.out2_c, inp1.get_slice(0, 1)),
                (
                    dut.out2_d,
                    inp1.get_bit(0)
                    @ inp1.get_bit(0)
                    @ inp1.get_slice(0, 2)
                    @ inp1.get_bit(4)
                    @ inp1.get_bit(1),
                ),
                (
                    dut.out2_e,
                    inp1.get_bit(4)
                    @ inp1.get_bit(3)
                    @ inp1.get_bit(2)
                    @ inp1.get_bit(1)
                    @ inp1.get_bit(0),
                ),
            ],
        )


class Unittest(unittest.TestCase):
    def test_slice(self):
        cocotb_util.run_cocotb_tests(test_slice_02, __file__, self.__module__)
