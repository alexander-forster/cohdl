from __future__ import annotations

import unittest

import itertools

import cohdl
from cohdl import BitVector, Port, Temporary
from cohdl import std

from cohdl_testutil import cocotb_util

context = None


def gen_entity():
    class test_local_fn_01(cohdl.Entity):
        inp_a = Port.input(BitVector[8])
        inp_b = Port.input(BitVector[8])

        result_1 = Port.output(BitVector[8])
        result_2 = Port.output(BitVector[8])
        result_3 = Port.output(BitVector[8])

        def architecture(self):
            @context
            def logic():
                def local_fn(a, result_2):
                    self.result_1 <<= a & self.inp_b
                    result_2 <<= a | self.inp_b
                    return a ^ self.inp_b

                self.result_3 <<= local_fn(self.inp_a, self.result_2)

    return test_local_fn_01


#
# test code
#


@cocotb_util.test()
async def testbench_local_fn_01(dut):
    ConstrainedGenerator = cocotb_util.ConstrainedGenerator
    bv_generator = ConstrainedGenerator(8)

    for a, b in itertools.product(
        bv_generator.random(16),
        bv_generator.random(16),
    ):
        await cocotb_util.check_concurrent(
            [
                (dut.inp_a, a),
                (dut.inp_b, b),
            ],
            [
                (dut.result_1, a & b),
                (dut.result_2, a | b),
                (dut.result_3, a ^ b),
            ],
        )


class Unittest(unittest.TestCase):
    def test_concurrent(self):
        global context
        context = std.concurrent
        cocotb_util.run_cocotb_tests(gen_entity(), __file__, self.__module__)

    def test_sequential(self):
        global context
        context = std.sequential
        cocotb_util.run_cocotb_tests(gen_entity(), __file__, self.__module__)
