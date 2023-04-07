from __future__ import annotations

import unittest

import itertools

import cohdl
from cohdl import Bit, BitVector, Port
from cohdl import std

from cohdl_testutil import cocotb_util


class test_any_all_02(cohdl.Entity):
    inp_a = Port.input(Bit)
    inp_b = Port.input(Bit)
    inp_c = Port.input(Bit)

    inp_bv = Port.inout(BitVector[4])

    out_any_abc = Port.output(Bit)
    out_all_abc = Port.output(Bit)

    out_any_list = Port.output(Bit)
    out_all_list = Port.output(Bit)

    out_any_bv = Port.output(Bit)
    out_all_bv = Port.inout(Bit)

    def architecture(self):
        l = [self.inp_a, self.inp_b, self.inp_c, self.inp_bv]

        @std.concurrent
        def logic():
            self.out_any_abc <<= any([self.inp_a, self.inp_b, self.inp_c])
            self.out_all_abc <<= all([self.inp_a, self.inp_b, self.inp_c])

            self.out_any_list <<= any([x for x in l])
            self.out_all_list <<= all([x for x in l])

            self.out_any_bv <<= any(self.inp_bv)
            self.out_all_bv <<= all(self.inp_bv)


#
# test code
#


@cocotb_util.test()
async def testbench_any_all_02(dut: test_any_all_02):
    ConstrainedGenerator = cocotb_util.ConstrainedGenerator
    bit_generator = ConstrainedGenerator(1)
    bv_generator = ConstrainedGenerator(4)

    for a, b, c, bv in itertools.product(
        bit_generator.all(),
        bit_generator.all(),
        bit_generator.all(),
        bv_generator.all(),
    ):

        await cocotb_util.check_concurrent(
            [(dut.inp_a, a), (dut.inp_b, b), (dut.inp_c, c), (dut.inp_bv, bv)],
            [
                (dut.out_any_abc, any([a, b, c])),
                (dut.out_all_abc, all([a, b, c])),
                (dut.out_any_list, any([a, b, c, bv])),
                (dut.out_all_list, all([a, b, c, bv])),
                (dut.out_any_bv, bool(bv)),
                (dut.out_all_bv, not bool(~bv)),
            ],
        )


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_any_all_02, __file__, self.__module__)
