from __future__ import annotations

import unittest

import itertools

import cohdl
from cohdl import Bit, BitVector, Port
from cohdl import std

from cohdl_testutil import cocotb_util


class test_on_exit_01(cohdl.Entity):
    clk = Port.input(Bit)
    inp_a = Port.input(BitVector[3])
    inp_b = Port.input(BitVector[3])

    out_a = Port.output(BitVector[3])
    out_b = Port.output(BitVector[3])

    def on_exit_b(self):
        @std.concurrent
        def logic():
            self.out_b <<= self.inp_b

    def architecture(self):
        def on_exit_a():
            @std.sequential
            def proc():
                self.out_a <<= self.inp_a

        cohdl.Block.on_exit(on_exit_a)
        cohdl.Block.on_exit(self.on_exit_b)


#
# test code
#


@cocotb_util.test()
async def testbench_match_simple(dut: test_on_exit_01):
    seq_test = cocotb_util.SequentialTest(dut.clk)

    ConstrainedGenerator = cocotb_util.ConstrainedGenerator
    vec_generator = ConstrainedGenerator(3)

    for vec_a, vec_b in itertools.product(vec_generator.all(), vec_generator.all()):
        await seq_test.check_next_tick(
            [
                (dut.inp_a, vec_a),
                (dut.inp_b, vec_b),
            ],
            [
                (dut.out_a, vec_a),
                (dut.out_b, vec_b),
            ],
        )


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_on_exit_01, __file__, self.__module__)
