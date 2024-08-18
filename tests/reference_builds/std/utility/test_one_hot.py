from __future__ import annotations

import unittest

import cohdl
from cohdl import std, BitVector, Unsigned, Signed, Port

from cohdl_testutil import cocotb_util

LEN_A = 1
LEN_B = 2
LEN_C = 8
LEN_D = 100


class test_one_hot(cohdl.Entity):

    pos_a = Port.input(Unsigned[8])
    pos_b = Port.input(Unsigned[8])
    pos_c = Port.input(Unsigned[8])
    pos_d = Port.input(Unsigned[8])

    out_a = Port.output(BitVector[LEN_A])
    out_b = Port.output(BitVector[LEN_B])
    out_c = Port.output(BitVector[LEN_C])
    out_d = Port.output(BitVector[LEN_D])

    val_a = Port.input(Unsigned[LEN_A])
    val_b = Port.input(Unsigned[LEN_B])
    val_c = Port.input(Unsigned[LEN_C])

    chk_a = Port.output(bool)
    chk_b = Port.output(bool)
    chk_c = Port.output(bool)

    def architecture(self):

        @cohdl.concurrent_context
        def logic():
            self.out_a <<= std.one_hot(LEN_A, self.pos_a)
            self.out_b <<= std.one_hot(LEN_B, self.pos_b)
            self.out_c <<= std.one_hot(LEN_C, self.pos_c)
            self.out_d <<= std.one_hot(LEN_D, self.pos_d)

            # check for a bug where bound statements of assertions
            # were evaluated twice
            # GHDL rejected this line before the fix
            assert 0 <= self.pos_a < 81, "check, that assertions work"

            self.chk_a <<= std.is_one_hot(self.val_a)
            self.chk_b <<= std.is_one_hot(self.val_b)
            self.chk_c <<= std.is_one_hot(self.val_c)


#
# test code
#


@cocotb_util.test()
async def testbench_one_hot(dut: test_one_hot):
    for input in range(256):
        a = input % LEN_A
        b = input % LEN_B
        c = input % LEN_C
        d = input % LEN_D

        val_a = input % 2**LEN_A
        val_b = input % 2**LEN_B
        val_c = input % 2**LEN_C

        dut.pos_a.value = a
        dut.pos_b.value = b
        dut.pos_c.value = c
        dut.pos_d.value = d

        dut.val_a.value = val_a
        dut.val_b.value = val_b
        dut.val_c.value = val_c

        await cocotb_util.step()

        assert dut.out_a.value == (1 << a)
        assert dut.out_b.value == (1 << b)
        assert dut.out_c.value == (1 << c)
        assert dut.out_d.value == (1 << d)

        assert dut.chk_a.value == (val_a.bit_count() == 1)
        assert dut.chk_b.value == (val_b.bit_count() == 1)
        assert dut.chk_c.value == (val_c.bit_count() == 1)


class Unittest(unittest.TestCase):
    def test_hdl(self):
        cocotb_util.run_cocotb_tests(test_one_hot, __file__, self.__module__)

    def test_python(self):
        for w in range(1, 5):
            for nr in range(w):
                oh = std.one_hot(w, nr)

                assert oh.unsigned == (1 << nr)
                assert std.is_one_hot(oh)

            for val in range(2**w):
                assert std.is_one_hot(Unsigned[w](val)) == (val.bit_count() == 1)
                assert std.is_one_hot(Signed[w + 1](val)) == (val.bit_count() == 1)

        assert std.is_one_hot(std.as_bitvector("1"))
        assert std.is_one_hot(std.as_bitvector("01"))
        assert std.is_one_hot(std.as_bitvector("10"))
        assert std.is_one_hot(std.as_bitvector("0001"))
        assert std.is_one_hot(std.as_bitvector("00100"))
