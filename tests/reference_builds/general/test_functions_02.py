from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Unsigned, select_with, Null, Full, enum

from cohdl import std

from cohdl_testutil import cocotb_util


class Fn:
    @staticmethod
    def ident(a):
        return a

    @staticmethod
    def nested_a(a):
        return Fn.ident(a)

    @staticmethod
    def nested_b(a):
        return Fn.nested_a(a)

    @staticmethod
    def option(cond, a, b):
        if cond:
            return a
        return b

    @staticmethod
    def option_b(cond, a, b):
        if cond:
            return a
        else:
            return b

    @staticmethod
    def option_nested(cond, a, b):
        if cond:
            return Fn.nested_b(a)
        return Fn.nested_b(b)

    @staticmethod
    def early_return(cond, a, b):
        if cond:
            return Fn.nested_b(a)
        if a:
            return a

        return a | b

    @staticmethod
    def early_return_2(cond, a, b):
        if cond:
            return Fn.nested_b(a)
        if a:
            return a

        if b:
            return b

        return Full


class test_function_simple(cohdl.Entity):
    clk = Port.input(Bit)

    a = Port.input(BitVector[4])
    b = Port.input(BitVector[4])
    cond = Port.input(Bit)

    out_ident = Port.output(BitVector[4])
    out_nested = Port.output(BitVector[4])
    out_nested_b = Port.output(BitVector[4])
    out_option = Port.output(BitVector[4])
    out_option_b = Port.output(BitVector[4])
    out_option_nested = Port.output(BitVector[4])
    out_early_return = Port.output(BitVector[4])
    out_early_return_2 = Port.output(BitVector[4])

    def architecture(self):
        clk = std.Clock(self.clk)

        @std.sequential(clk)
        def proc_simple():
            self.out_ident <<= Fn.ident(self.a)
            self.out_nested <<= Fn.nested_a(self.a)
            self.out_nested_b <<= Fn.nested_b(self.a)
            self.out_option <<= Fn.option(self.cond, self.a, self.b)
            self.out_option_b <<= Fn.option_b(self.cond, self.a, self.b)
            self.out_option_nested <<= Fn.option_nested(self.cond, self.a, self.b)
            self.out_early_return <<= Fn.early_return(self.cond, self.a, self.b)
            self.out_early_return_2 <<= Fn.early_return_2(self.cond, self.a, self.b)


#
# test code
#


@cocotb_util.test()
async def testbench_function_simple(dut: test_function_simple):
    seq = cocotb_util.SequentialTest(dut.clk)

    ab_gen = cocotb_util.ConstrainedGenerator(4)
    cond_gen = cocotb_util.ConstrainedGenerator(1)

    for a in ab_gen.all():
        for b in ab_gen.all():
            for cond in cond_gen.all():

                if cond:
                    early_return = a
                    early_return_2 = a
                else:
                    if a:
                        early_return = a
                        early_return_2 = a
                    else:
                        early_return = b

                        if b:
                            early_return_2 = b
                        else:
                            early_return_2 = "1111"

                await seq.check_next_tick(
                    [(dut.a, a), (dut.b, b), (dut.cond, cond)],
                    [
                        (dut.out_ident, a),
                        (dut.out_nested, a),
                        (dut.out_nested_b, a),
                        (dut.out_option, a if cond else b),
                        (dut.out_option_b, a if cond else b),
                        (dut.out_option_nested, a if cond else b),
                        (dut.out_early_return, early_return),
                        (dut.out_early_return_2, early_return_2),
                    ],
                    check_msg=f"{a=}, {b=}, {cond=}",
                )


class Unittest(unittest.TestCase):
    def test_function_simple(self):
        cocotb_util.run_cocotb_tests(test_function_simple, __file__, self.__module__)
