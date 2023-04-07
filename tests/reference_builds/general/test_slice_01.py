from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port
from cohdl import std

from cohdl_testutil import cocotb_util


class test_slice_01(cohdl.Entity):
    inp1 = Port.input(BitVector[5])
    inp2 = Port.input(BitVector[5])

    out2_lsb = Port.output(Bit)
    out2_msb = Port.output(Bit)
    out2_lsb_3 = Port.output(BitVector[3])
    out2_msb_3 = Port.output(BitVector[3])

    out2_seq_l2_m = Port.output(Bit)
    out2_seq_m2_l = Port.output(Bit)
    out2_seq_l4_m3 = Port.output(BitVector[3])
    out2_seq_m4_l3 = Port.output(BitVector[3])
    out2_seq_l5_m5_l4_m2 = Port.output(BitVector[2])
    out2_seq_m5_l5_m4_l2 = Port.output(BitVector[2])

    def architecture(self):
        @std.concurrent
        def logic():
            self.out2_lsb <<= self.inp2.lsb()
            self.out2_msb <<= self.inp2.msb()
            self.out2_lsb_3 <<= self.inp2.lsb(3)
            self.out2_msb_3 <<= self.inp2.msb(3)

            self.out2_seq_l2_m <<= self.inp2.lsb(2).msb()
            self.out2_seq_m2_l <<= self.inp2.msb(2).lsb()
            self.out2_seq_l4_m3 <<= self.inp2.lsb(4).msb(3)
            self.out2_seq_m4_l3 <<= self.inp2.msb(4).lsb(3)

            self.out2_seq_l5_m5_l4_m2 <<= self.inp2.lsb(5).msb(5).lsb(4).msb(2)
            self.out2_seq_m5_l5_m4_l2 <<= self.inp2.msb(5).lsb(5).msb(4).lsb(2)


#
# test code
#


@cocotb_util.test()
async def testbench_match_simple(dut: test_slice_01):
    inp_1_gen = cocotb_util.ConstrainedGenerator(5)
    inp_2_gen = cocotb_util.ConstrainedGenerator(5)

    for inp1 in inp_1_gen.all():
        for inp2 in inp_2_gen.all():
            await cocotb_util.check_concurrent(
                [
                    (dut.inp1, inp1),
                    (dut.inp2, inp2),
                ],
                [
                    (dut.out2_lsb, inp2.get_bit(0)),
                    (dut.out2_msb, inp2.get_bit(-1)),
                    (dut.out2_lsb_3, inp2.get_slice(0, 2)),
                    (dut.out2_msb_3, inp2.get_slice(2, 4)),
                    (dut.out2_seq_l4_m3, inp2.get_slice(1, 3)),
                    (dut.out2_seq_m4_l3, inp2.get_slice(1, 3)),
                    (dut.out2_seq_l5_m5_l4_m2, inp2.get_slice(2, 3)),
                    (dut.out2_seq_m5_l5_m4_l2, inp2.get_slice(1, 2)),
                ],
            )


class Unittest(unittest.TestCase):
    def test_slice(self):
        cocotb_util.run_cocotb_tests(test_slice_01, __file__, self.__module__)
