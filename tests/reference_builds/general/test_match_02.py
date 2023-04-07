from __future__ import annotations

import unittest

import itertools

import cohdl
from cohdl import Bit, BitVector, Port, Null, Full
from cohdl import std

from cohdl_testutil import cocotb_util


class test_match_02(cohdl.Entity):
    clk = Port.input(Bit)

    op = Port.input(BitVector[2])

    inp_vec_a = Port.input(BitVector[3])
    inp_vec_b = Port.input(BitVector[3])
    out_vec = Port.output(BitVector[3])

    inp_bit_a = Port.input(Bit)
    inp_bit_b = Port.input(Bit)
    out_bit = Port.output(Bit)

    def architecture(self):
        clk = std.Clock(self.clk)

        @std.sequential(clk)
        def proc_simple():
            match self.op:
                case "00":
                    self.out_vec <<= self.inp_vec_a & self.inp_vec_b
                    self.out_bit <<= self.inp_bit_a & self.inp_bit_b
                case "01":
                    self.out_vec <<= self.inp_vec_a | self.inp_vec_b
                    self.out_bit <<= self.inp_bit_a | self.inp_bit_b
                case "10":
                    self.out_vec <<= self.inp_vec_a ^ self.inp_vec_b
                    self.out_bit <<= self.inp_bit_a ^ self.inp_bit_b
                case "11":
                    self.out_vec <<= Full
                    self.out_bit <<= Null
                case _:
                    pass


#
# test code
#


@cocotb_util.test()
async def testbench_match_simple(dut: test_match_02):
    seq_test = cocotb_util.SequentialTest(dut.clk)

    ConstrainedGenerator = cocotb_util.ConstrainedGenerator
    op_generator = ConstrainedGenerator(2)
    vec_generator = ConstrainedGenerator(3)
    bit_generator = ConstrainedGenerator(1)

    for op, vec_a, vec_b, bit_a, bit_b in itertools.product(
        op_generator.all(),
        vec_generator.all(),
        vec_generator.all(),
        bit_generator.all(),
        bit_generator.all(),
    ):
        match op.as_str():
            case "00":
                out_vec = vec_a & vec_b
                out_bit = bit_a & bit_b
            case "01":
                out_vec = vec_a | vec_b
                out_bit = bit_a | bit_b
            case "10":
                out_vec = vec_a ^ vec_b
                out_bit = bit_a ^ bit_b
            case "11":
                out_vec = vec_generator.full()
                out_bit = vec_generator.null()
            case _:
                raise AssertionError("invalid test case")

        await seq_test.check_next_tick(
            [
                (dut.op, op),
                (dut.inp_vec_a, vec_a),
                (dut.inp_vec_b, vec_b),
                (dut.inp_bit_a, bit_a),
                (dut.inp_bit_b, bit_b),
            ],
            [
                (dut.out_vec, out_vec),
                (dut.out_bit, out_bit),
            ],
        )


class Unittest(unittest.TestCase):
    def test_match_simple(self):
        cocotb_util.run_cocotb_tests(test_match_02, __file__, self.__module__)
