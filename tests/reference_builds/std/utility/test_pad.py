from __future__ import annotations

import unittest

import cohdl
from cohdl import std, Bit, BitVector, Unsigned, Signed, Port, Null, Full

from cohdl_testutil import cocotb_util
import random


class test_pad(cohdl.Entity):
    inp_bit = Port.input(Bit)
    inp_a = Port.input(BitVector[1])
    inp_b = Port.input(Unsigned[4])

    left_a_1 = Port.output(BitVector[1])
    left_a_2 = Port.output(BitVector[2])
    left_a_4 = Port.output(BitVector[4])
    left_a_8_bit = Port.output(BitVector[8])
    left_a_8_null = Port.output(BitVector[8])
    left_a_8_full = Port.output(BitVector[8])

    right_b_4 = Port.output(BitVector[4])
    right_b_5 = Port.output(BitVector[5])
    right_b_7 = Port.output(BitVector[7])
    right_b_8_bit = Port.output(BitVector[8])
    right_b_8_null = Port.output(BitVector[8])
    right_b_8_full = Port.output(BitVector[8])

    def architecture(self):
        def is_bv(arg):
            assert std.instance_check(arg, BitVector)
            assert not std.instance_check(arg, Unsigned)
            assert not std.instance_check(arg, Signed)
            return arg

        @std.concurrent
        def logic():
            self.left_a_1 <<= is_bv(std.leftpad(self.inp_a, 1))
            self.left_a_2 <<= is_bv(std.leftpad(self.inp_a, 2))
            self.left_a_4 <<= is_bv(std.leftpad(self.inp_a, 4))
            self.left_a_8_bit <<= is_bv(std.leftpad(self.inp_a, 8, self.inp_bit))
            self.left_a_8_null <<= is_bv(std.leftpad(self.inp_a, 8, Null))
            self.left_a_8_full <<= is_bv(std.leftpad(self.inp_a, 8, Full))

            self.right_b_4 <<= is_bv(std.rightpad(self.inp_b, 4))
            self.right_b_5 <<= is_bv(std.rightpad(self.inp_b, 5))
            self.right_b_7 <<= is_bv(std.rightpad(self.inp_b, 7, Bit(False)))
            self.right_b_8_bit <<= is_bv(std.rightpad(self.inp_b, 8, self.inp_bit))
            self.right_b_8_null <<= is_bv(std.rightpad(self.inp_b, 8, Null))
            self.right_b_8_full <<= is_bv(std.rightpad(self.inp_b, 8, Full))


#
# test code
#


@cocotb_util.test()
async def testbench_pad(dut: test_pad):
    for _ in range(64):
        inp_bit = random.randint(0, 1)
        inp_a = random.randint(0, 1)
        inp_b = random.randint(0, 15)

        dut.inp_bit.value = inp_bit
        dut.inp_a.value = inp_a
        dut.inp_b.value = inp_b

        await cocotb_util.step()

        assert dut.left_a_1 == inp_a
        assert dut.left_a_2 == inp_a
        assert dut.left_a_4 == inp_a
        assert dut.left_a_8_bit == ((0xFE | inp_a) if inp_bit else inp_a)
        assert dut.left_a_8_null == inp_a
        assert dut.left_a_8_full == (0xFE | inp_a)

        assert dut.right_b_4 == inp_b
        assert dut.right_b_5 == inp_b << 1
        assert dut.right_b_7 == inp_b << 3
        assert dut.right_b_8_bit == (inp_b << 4) | (inp_bit and 0xF)
        assert dut.right_b_8_null == inp_b << 4
        assert dut.right_b_8_full == (inp_b << 4) | 0xF


class Unittest(unittest.TestCase):
    def test_hdl(self):
        cocotb_util.run_cocotb_tests(test_pad, __file__, self.__module__)

    def test_python(self):
        assert std.leftpad(std.ones(5), 8) == std.as_bitvector("00011111")
        assert std.leftpad(std.ones(5), 8, Full) == std.as_bitvector("11111111")
        assert std.leftpad(std.ones(5), 8, Bit(0)) == std.as_bitvector("00011111")
        assert std.rightpad(std.ones(5), 8) == std.as_bitvector("11111000")
        assert std.rightpad(std.ones(5), 8, Full) == std.as_bitvector("11111111")
        assert std.rightpad(std.ones(5), 8, Bit(1)) == std.as_bitvector("11111111")
