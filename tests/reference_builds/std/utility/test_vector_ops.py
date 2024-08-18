from __future__ import annotations

import unittest

import cohdl
from cohdl import (
    std,
    Bit,
    BitVector,
    Unsigned,
    Signed,
    Port,
    Null,
    Full,
    AssignMode,
    Variable,
)

from cohdl_testutil import cocotb_util
import random


def is_bv(arg):
    assert std.instance_check(arg, BitVector)
    assert not std.instance_check(arg, Unsigned)
    assert not std.instance_check(arg, Signed)
    return arg


class test_vector_ops(cohdl.Entity):
    inp_bit = Port.input(Bit)
    inp_a = Port.input(BitVector[1])
    inp_b = Port.input(Unsigned[4])

    repeat_bit_1 = Port.output(BitVector[1])
    repeat_bit_2 = Port.output(BitVector[2])
    repeat_bit_3 = Port.output(BitVector[3])
    repeat_bit_7 = Port.output(BitVector[7])
    repeat_bit_8 = Port.output(BitVector[8])

    repeat_a_1 = Port.output(BitVector[1])
    repeat_a_2 = Port.output(BitVector[2])
    repeat_a_3 = Port.output(BitVector[3])
    repeat_a_7 = Port.output(BitVector[7])
    repeat_a_8 = Port.output(BitVector[8])

    repeat_b_1 = Port.output(BitVector[4])
    repeat_b_2 = Port.output(BitVector[8])
    repeat_b_3 = Port.output(BitVector[12])
    repeat_b_7 = Port.output(BitVector[28])
    repeat_b_8 = Port.output(BitVector[32])

    stretch_bit_1 = Port.output(BitVector[1])
    stretch_bit_2 = Port.output(BitVector[2])
    stretch_bit_3 = Port.output(BitVector[3])
    stretch_bit_8 = Port.output(BitVector[8])
    stretch_bit_9 = Port.output(BitVector[9])

    stretch_a_1 = Port.output(BitVector[1])
    stretch_a_2 = Port.output(BitVector[2])
    stretch_a_3 = Port.output(BitVector[3])
    stretch_a_7 = Port.output(BitVector[7])
    stretch_a_11 = Port.output(BitVector[11])

    stretch_b_1 = Port.output(BitVector[4])
    stretch_b_2 = Port.output(BitVector[8])
    stretch_b_3 = Port.output(BitVector[12])
    stretch_b_4 = Port.output(BitVector[16])
    stretch_b_5 = Port.output(BitVector[20])

    concat_bit = Port.output(BitVector[1])
    concat_a = Port.output(BitVector[1])
    concat_b = Port.output(BitVector[4])

    concat_bit_bit = Port.output(BitVector[2])
    concat_a_a = Port.output(BitVector[2])
    concat_b_b = Port.output(BitVector[8])

    concat_bit_a = Port.output(BitVector[2])
    concat_a_bit = Port.output(BitVector[2])
    concat_bit_b = Port.output(BitVector[5])
    concat_b_bit = Port.output(BitVector[5])
    concat_a_b = Port.output(BitVector[5])
    concat_b_a = Port.output(BitVector[5])

    concat_bit_a_b = Port.output(BitVector[6])
    concat_b_bit_a = Port.output(BitVector[6])
    concat_a_b_bit = Port.output(BitVector[6])

    concat_a_b_b_a = Port.output(BitVector[10])
    concat_a_b_b_a_a = Port.output(BitVector[11])
    concat_b_a_b_a_b_a = Port.output(BitVector[15])

    def architecture(self):

        @std.concurrent
        def logic_assign():
            # also test std.assign

            self.repeat_bit_1 <<= is_bv(std.repeat(self.inp_bit, 1))
            std.assign(self.repeat_bit_2, is_bv(std.repeat(self.inp_bit, 2)))
            std.assign(
                self.repeat_bit_3, is_bv(std.repeat(self.inp_bit, 3)), AssignMode.NEXT
            )

            std.assign(
                self.repeat_bit_7,
                is_bv(std.repeat(self.inp_bit, 7)),
                mode=AssignMode.AUTO,
            )
            self.repeat_bit_8 <<= is_bv(std.repeat(self.inp_bit, times=8))

        @std.sequential
        def proc_assign(
            var_a_7=Variable[BitVector[7]](), var_a_8=Variable[BitVector[8]]()
        ):

            self.repeat_a_1 <<= is_bv(std.repeat(self.inp_a.signed, 1))
            std.assign(self.repeat_a_2, is_bv(std.repeat(self.inp_a.unsigned, 2)))
            self.repeat_a_3 <<= is_bv(std.repeat(self.inp_a, times=3))

            std.assign(var_a_7, is_bv(std.repeat(self.inp_a.signed, 7)))
            std.assign(var_a_8, is_bv(std.repeat(self.inp_a, 8)), AssignMode.VALUE)

            self.repeat_a_7 <<= var_a_7
            std.assign(self.repeat_a_8, var_a_8)

            self.repeat_b_1 <<= is_bv(std.repeat(self.inp_b, times=1))
            self.repeat_b_2 <<= is_bv(std.repeat(self.inp_b, 2))
            self.repeat_b_3 <<= is_bv(std.repeat(self.inp_b.signed, 3))
            self.repeat_b_7 <<= is_bv(std.repeat(self.inp_b, 7))
            self.repeat_b_8 <<= is_bv(std.repeat(self.inp_b.unsigned, 8))

            #

        @std.concurrent
        def logic():
            self.stretch_bit_1 <<= is_bv(std.stretch(self.inp_bit, factor=1))
            self.stretch_bit_2 <<= is_bv(std.stretch(self.inp_bit, 2))
            self.stretch_bit_3 <<= is_bv(std.stretch(self.inp_bit, 3))
            self.stretch_bit_8 <<= is_bv(std.stretch(self.inp_bit, 8))
            self.stretch_bit_9 <<= is_bv(std.stretch(self.inp_bit, 9))

            self.stretch_a_1 <<= is_bv(std.stretch(self.inp_a.signed, 1))
            self.stretch_a_2 <<= is_bv(std.stretch(self.inp_a.unsigned, 2))
            self.stretch_a_3 <<= is_bv(std.stretch(self.inp_a, factor=3))
            self.stretch_a_7 <<= is_bv(std.stretch(self.inp_a.signed, 7))
            self.stretch_a_11 <<= is_bv(std.stretch(self.inp_a, 11))

            self.stretch_b_1 <<= is_bv(std.stretch(self.inp_b, 1))
            self.stretch_b_2 <<= is_bv(std.stretch(self.inp_b, 2))
            self.stretch_b_3 <<= is_bv(std.stretch(self.inp_b.signed, 3))
            self.stretch_b_4 <<= is_bv(std.stretch(self.inp_b, factor=4))
            self.stretch_b_5 <<= is_bv(std.stretch(self.inp_b.unsigned, 5))

            #

            self.concat_bit <<= is_bv(std.concat(self.inp_bit))
            self.concat_a <<= is_bv(std.concat(self.inp_a.signed))
            self.concat_b <<= is_bv(std.concat(self.inp_b.unsigned))

            self.concat_bit_bit <<= is_bv(std.concat(self.inp_bit, self.inp_bit))
            self.concat_a_a <<= is_bv(std.concat(self.inp_a, self.inp_a))
            self.concat_b_b <<= is_bv(std.concat(self.inp_b, self.inp_b))

            self.concat_bit_a <<= is_bv(std.concat(self.inp_bit, self.inp_a))
            self.concat_a_bit <<= is_bv(std.concat(self.inp_a, self.inp_bit))
            self.concat_bit_b <<= is_bv(std.concat(self.inp_bit, self.inp_b))
            self.concat_b_bit <<= is_bv(std.concat(self.inp_b, self.inp_bit))
            self.concat_a_b <<= is_bv(std.concat(self.inp_a, self.inp_b))
            self.concat_b_a <<= is_bv(std.concat(self.inp_b, self.inp_a))

            self.concat_a_b_b_a <<= is_bv(
                std.concat(self.inp_a, self.inp_b, self.inp_b, self.inp_a)
            )

            self.concat_a_b_b_a_a <<= is_bv(
                std.concat(self.inp_a, self.inp_b, self.inp_b, self.inp_a, self.inp_a)
            )

            self.concat_b_a_b_a_b_a <<= is_bv(
                std.concat(
                    self.inp_b,
                    self.inp_a,
                    self.inp_b,
                    self.inp_a,
                    self.inp_b,
                    self.inp_a,
                )
            )


#
# test code
#


def repeat(width: int, val: int, times: int):
    result = 0

    for _ in range(times):
        result = (result << width) | val

    return result


def stretch(width: int, val: int, times: int):
    result = 0

    for n in range(0, width)[::-1]:
        bit = bool(val & (1 << n))
        for _ in range(times):
            result = (result << 1) | bit

    return result


def concat(*args: tuple[int, int]):
    result = 0

    for w, val in args:
        result = (result << w) | val

    return result


@cocotb_util.test()
async def testbench_vector_ops(dut: test_vector_ops):

    for _ in range(64):
        inp_bit = random.randint(0, 1)
        inp_a = random.randint(0, 1)
        inp_b = random.randint(0, 15)

        dut.inp_bit.value = inp_bit
        dut.inp_a.value = inp_a
        dut.inp_b.value = inp_b

        await cocotb_util.step()

        assert dut.repeat_bit_1 == repeat(1, inp_bit, 1)
        assert dut.repeat_bit_2 == repeat(1, inp_bit, 2)
        assert dut.repeat_bit_3 == repeat(1, inp_bit, 3)
        assert dut.repeat_bit_7 == repeat(1, inp_bit, 7)
        assert dut.repeat_bit_8 == repeat(1, inp_bit, 8)

        assert dut.repeat_a_1 == repeat(1, inp_a, 1)
        assert dut.repeat_a_2 == repeat(1, inp_a, 2)
        assert dut.repeat_a_3 == repeat(1, inp_a, 3)
        assert dut.repeat_a_7 == repeat(1, inp_a, 7)
        assert dut.repeat_a_8 == repeat(1, inp_a, 8)

        assert dut.repeat_b_1 == repeat(4, inp_b, 1)
        assert dut.repeat_b_2 == repeat(4, inp_b, 2)
        assert dut.repeat_b_3 == repeat(4, inp_b, 3)
        assert dut.repeat_b_7 == repeat(4, inp_b, 7)
        assert dut.repeat_b_8 == repeat(4, inp_b, 8)

        #

        assert dut.stretch_bit_1 == stretch(1, inp_bit, 1)
        assert dut.stretch_bit_2 == stretch(1, inp_bit, 2)
        assert dut.stretch_bit_3 == stretch(1, inp_bit, 3)
        assert dut.stretch_bit_8 == stretch(1, inp_bit, 8)
        assert dut.stretch_bit_9 == stretch(1, inp_bit, 9)

        assert dut.stretch_a_1 == stretch(1, inp_a, 1)
        assert dut.stretch_a_2 == stretch(1, inp_a, 2)
        assert dut.stretch_a_3 == stretch(1, inp_a, 3)
        assert dut.stretch_a_7 == stretch(1, inp_a, 7)
        assert dut.stretch_a_11 == stretch(1, inp_a, 11)

        assert dut.stretch_b_1 == stretch(4, inp_b, 1)
        assert dut.stretch_b_2 == stretch(4, inp_b, 2)
        assert dut.stretch_b_3 == stretch(4, inp_b, 3)
        assert dut.stretch_b_4 == stretch(4, inp_b, 4)
        assert dut.stretch_b_5 == stretch(4, inp_b, 5)

        #

        c_bit = (1, inp_bit)
        c_a = (1, inp_a)
        c_b = (4, inp_b)

        assert dut.concat_bit == inp_bit
        assert dut.concat_a == inp_a
        assert dut.concat_b == inp_b

        assert dut.concat_bit_bit == concat(c_bit, c_bit)
        assert dut.concat_a_a == concat(c_a, c_a)
        assert dut.concat_b_b == concat(c_b, c_b)

        assert dut.concat_bit_a == concat(c_bit, c_a)
        assert dut.concat_a_bit == concat(c_a, c_bit)
        assert dut.concat_bit_b == concat(c_bit, c_b)
        assert dut.concat_b_bit == concat(c_b, c_bit)
        assert dut.concat_a_b == concat(c_a, c_b)
        assert dut.concat_b_a == concat(c_b, c_a)

        assert dut.concat_a_b_b_a == concat(c_a, c_b, c_b, c_a)
        assert dut.concat_a_b_b_a_a == concat(c_a, c_b, c_b, c_a, c_a)
        assert dut.concat_b_a_b_a_b_a == concat(c_b, c_a, c_b, c_a, c_b, c_a)


class Unittest(unittest.TestCase):
    def test_hdl(self):
        cocotb_util.run_cocotb_tests(test_vector_ops, __file__, self.__module__)

    def test_python(self):
        bv = std.as_bitvector

        assert is_bv(std.repeat(Bit(Null), 1)) == bv("0")
        assert is_bv(std.repeat(Bit(Full), 2)) == bv("11")
        assert is_bv(std.repeat(Bit(1), 3)) == bv("111")
        assert is_bv(std.repeat(Bit(False), 4)) == bv("0000")

        assert is_bv(std.repeat(bv("1"), 1)) == bv("1")
        assert is_bv(std.repeat(bv("101").unsigned, 1)) == bv("101")
        assert is_bv(std.repeat(bv("1").signed, 1)) == bv("1")
        assert is_bv(std.repeat(bv("0011"), 1)) == bv("0011")

        assert is_bv(std.repeat(bv("1"), 2)) == bv("11")
        assert is_bv(std.repeat(bv("101").unsigned, 2)) == bv("101101")
        assert is_bv(std.repeat(bv("1").signed, 2)) == bv("11")
        assert is_bv(std.repeat(bv("0011"), 2)) == bv("00110011")

        assert is_bv(std.repeat(bv("1"), 3)) == bv("111")
        assert is_bv(std.repeat(bv("101").unsigned, 3)) == bv("101101101")
        assert is_bv(std.repeat(bv("1").signed, 3)) == bv("111")
        assert is_bv(std.repeat(bv("0011"), 3)) == bv("001100110011")

        #

        assert is_bv(std.stretch(Bit(Null), 1)) == bv("0")
        assert is_bv(std.stretch(Bit(Full), 2)) == bv("11")
        assert is_bv(std.stretch(Bit(1), 3)) == bv("111")
        assert is_bv(std.stretch(Bit(False), 4)) == bv("0000")

        assert is_bv(std.stretch(bv("1"), 1)) == bv("1")
        assert is_bv(std.stretch(bv("101").unsigned, 1)) == bv("101")
        assert is_bv(std.stretch(bv("1").signed, 1)) == bv("1")
        assert is_bv(std.stretch(bv("0011"), 1)) == bv("0011")

        assert is_bv(std.stretch(bv("1"), 2)) == bv("11")
        assert is_bv(std.stretch(bv("101").unsigned, 2)) == bv("110011")
        assert is_bv(std.stretch(bv("1").signed, 2)) == bv("11")
        assert is_bv(std.stretch(bv("0011"), 2)) == bv("00001111")

        assert is_bv(std.stretch(bv("1"), 3)) == bv("111")
        assert is_bv(std.stretch(bv("101").unsigned, 3)) == bv("111000111")
        assert is_bv(std.stretch(bv("1").signed, 3)) == bv("111")
        assert is_bv(std.stretch(bv("0011"), 3)) == bv("000000111111")

        #

        assert is_bv(std.concat(Bit(Null))) == bv("0")
        assert is_bv(std.concat(Bit(Full))) == bv("1")

        assert is_bv(std.concat(Bit(Null), Bit(1))) == bv("01")
        assert is_bv(std.concat(Bit(Full), Bit(0))) == bv("10")

        assert is_bv(std.concat(bv("1011"))) == bv("1011")
        assert is_bv(std.concat(bv("1101").unsigned)) == bv("1101")
        assert is_bv(std.concat(bv("1110").signed)) == bv("1110")

        assert is_bv(std.concat(Bit(Null), bv("01"), bv("1111"))) == bv("0011111")
