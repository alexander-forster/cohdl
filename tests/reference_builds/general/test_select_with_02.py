from __future__ import annotations

import unittest

import itertools

import cohdl
from cohdl import Bit, BitVector, Port, Null, Full, select_with, Unsigned, Signed
from cohdl import std

from cohdl_testutil import cocotb_util

keys = ["00", "01", "10", "11"]


def gen_entity():
    # this function is required because
    # entities are only evaluated once
    # an changes to key would not affect
    # the vhdl representaion otherwise
    class test_select_with_02(cohdl.Entity):
        clk = Port.input(Bit)

        op = Port.input(BitVector[2])

        inp_vec_a = Port.input(BitVector[3])
        inp_vec_b = Port.input(BitVector[3])
        out_vec = Port.output(BitVector[3])
        out_unsigned = Port.output(Unsigned[5])
        out_signed = Port.output(Signed[6])

        inp_bit_a = Port.input(Bit)
        inp_bit_b = Port.input(Bit)
        out_bit = Port.output(Bit)

        def architecture(self):
            clk = std.Clock(self.clk)

            @std.sequential(clk)
            def proc_simple():

                self.out_vec <<= select_with(
                    self.op,
                    {
                        keys[0]: self.inp_vec_a & self.inp_vec_b,
                        keys[1]: self.inp_vec_a | self.inp_vec_b,
                        keys[2]: self.inp_vec_a ^ self.inp_vec_b,
                        keys[3]: Full,
                    },
                )

                self.out_unsigned <<= select_with(
                    self.op,
                    {
                        keys[0]: self.inp_vec_a.unsigned & self.inp_vec_b.unsigned,
                        keys[1]: self.inp_vec_a.unsigned | self.inp_vec_b.unsigned,
                        keys[2]: self.inp_vec_a.unsigned ^ self.inp_vec_b.unsigned,
                        keys[3]: Full,
                    },
                )

                self.out_signed <<= select_with(
                    self.op,
                    {
                        keys[0]: self.inp_vec_a.signed & self.inp_vec_b.signed,
                        keys[1]: Null,
                        keys[2]: self.inp_vec_a.unsigned ^ self.inp_vec_b.unsigned,
                        keys[3]: Full,
                    },
                )

                self.out_bit <<= select_with(
                    self.op,
                    {
                        keys[0]: self.inp_bit_a & self.inp_bit_b,
                        keys[1]: self.inp_bit_a | self.inp_bit_b,
                        keys[2]: self.inp_bit_a ^ self.inp_bit_b,
                        keys[3]: Null,
                    },
                )

    return test_select_with_02


#
# test code
#


@cocotb_util.test()
async def testbench_match_simple(dut):
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
                out_unsigned = vec_a & vec_b
                out_signed = (vec_a & vec_b).signed()
            case "01":
                out_vec = vec_a | vec_b
                out_bit = bit_a | bit_b
                out_unsigned = vec_a | vec_b
                out_signed = 0
            case "10":
                out_vec = vec_a ^ vec_b
                out_bit = bit_a ^ bit_b
                out_unsigned = vec_a ^ vec_b
                out_signed = vec_a ^ vec_b
            case "11":
                out_vec = vec_generator.full()
                out_bit = vec_generator.null()
                out_unsigned = (1 << 5) - 1
                out_signed = -1
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
                (dut.out_unsigned, out_unsigned),
                (dut.out_signed, out_signed),
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
