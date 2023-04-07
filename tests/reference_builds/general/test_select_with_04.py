from __future__ import annotations

import unittest

import itertools

import cohdl
from cohdl import Bit, BitVector, Port, Null, Full, select_with
from cohdl import std

from cohdl_testutil import cocotb_util

keys = ["00", "01", "10", "11"]


def gen_entity():
    # this function is required because
    # entities are only evaluated once
    # an changes to key would not affect
    # the vhdl representaion otherwise
    class test_select_with_04(cohdl.Entity):
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
                vectors = [
                    self.inp_vec_a & self.inp_vec_b,
                    self.inp_vec_a | self.inp_vec_b,
                    self.inp_vec_a ^ self.inp_vec_b,
                    Full,
                ]

                bits = [
                    self.inp_bit_a & self.inp_bit_b,
                    self.inp_bit_a | self.inp_bit_b,
                    self.inp_bit_a ^ self.inp_bit_b,
                    Null,
                ]

                self.out_vec <<= select_with(
                    self.op, {key: vec for key, vec in zip(keys, vectors)}
                )

                key_bit_pairs = [(key, bit) for key, bit in zip(keys, bits)]

                self.out_bit <<= select_with(
                    self.op, {key: bit for key, bit in key_bit_pairs}
                )

    return test_select_with_04


#
# test code
#


@cocotb_util.test()
async def testbench_select_with_04(dut):
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
    def test_keys_str(self):
        global keys
        keys = ["00", "01", "10", "11"]
        cocotb_util.run_cocotb_tests(gen_entity(), __file__, self.__module__)

    def test_keys_bitvector(self):
        global keys
        keys = [
            BitVector[2]("00"),
            BitVector[2]("01"),
            BitVector[2]("10"),
            BitVector[2]("11"),
        ]
        cocotb_util.run_cocotb_tests(gen_entity(), __file__, self.__module__)

    def test_keys_mixed_1(self):
        global keys
        keys = [
            "00",
            BitVector[2]("01"),
            BitVector[2]("10"),
            BitVector[2]("11"),
        ]
        cocotb_util.run_cocotb_tests(gen_entity(), __file__, self.__module__)

    def test_keys_mixed_2(self):
        global keys
        keys = [
            BitVector[2]("00"),
            BitVector[2]("01"),
            BitVector[2]("10"),
            "11",
        ]
        cocotb_util.run_cocotb_tests(gen_entity(), __file__, self.__module__)
