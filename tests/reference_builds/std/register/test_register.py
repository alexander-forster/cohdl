from __future__ import annotations

import unittest

import cohdl
from cohdl import std, Bit, BitVector, Port, Unsigned, Signal

from cohdl.std.bitfield import bitfield, Field

import cohdl_testutil
from cohdl_testutil import cocotb_util

import random
import cocotb


@bitfield
class TestRegister:
    a: Field[0]
    b: Field[1]
    c: Field[4:2]
    d: Field[15:0]
    e: Field[3:0].Unsigned


class test_register_simple(cohdl.Entity):
    inp_vector = Port.input(BitVector[16])

    out_a = Port.output(Bit)
    out_b = Port.output(Bit)
    out_c = Port.output(BitVector[3])
    out_d = Port.output(BitVector[16])

    out_sum = Port.output(Unsigned[5])

    def architecture(self):
        my_reg = TestRegister(self.inp_vector)

        e = Signal[BitVector[5]]()
        x = e[3:1]

        @std.concurrent
        def proc_simple():
            self.out_a <<= my_reg.a
            self.out_b <<= my_reg.b
            self.out_c <<= my_reg.c
            self.out_d <<= my_reg.d
            self.out_sum <<= my_reg.e + 1
            # self.out_sum <<= x.unsigned + 1


@cocotb.test()
async def testbench_function_simple(dut: test_register_simple):
    for _ in range(100):
        test_value = random.randint(0, 2**16 - 1)

        await cocotb_util.check_concurrent(
            [(dut.inp_vector, test_value)],
            [
                (dut.out_a, bool(test_value & 1)),
                (dut.out_b, bool(test_value & 2)),
                (dut.out_sum, ((test_value & 0xF) + 1) & 0xF),
            ],
            check_msg=f"{test_value=}",
        )


class Unittest(unittest.TestCase):
    def test_register_simple(self):
        cohdl_testutil.run_cocotb_tests(test_register_simple, __file__, self.__module__)
