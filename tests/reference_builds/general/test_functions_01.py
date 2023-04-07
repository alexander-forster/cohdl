from __future__ import annotations

from typing import Any, Tuple
import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Unsigned, Signed, select_with, Null, Full, enum

from cohdl import std

from cohdl_testutil import cocotb_util


class Fn:
    @staticmethod
    def ident(a):
        return a

    @staticmethod
    def nested_ident(a):
        return Fn.ident(a)

    @staticmethod
    def select(cond, a, b):
        return a if cond else b

    @staticmethod
    def select_nested(cond, a, b):
        return Fn.select(cond, a, b)


class test_functions(cohdl.Entity):
    sw = Port.input(BitVector[4])

    ident_in = Port.input(BitVector[4])
    ident_in_2 = Port.input(BitVector[4])
    ident_out = Port.output(BitVector[4])
    ident_out_2 = Port.output(BitVector[4])

    sel_bit = Port.input(Bit)
    selected = Port.output(BitVector[4])
    selected_2 = Port.output(BitVector[4])
    selected_nullfull = Port.output(BitVector[4])

    def architecture(self):
        @std.concurrent
        def logic_simple():
            self.ident_out <<= Fn.ident(self.ident_in)
            self.ident_out_2 <<= Fn.nested_ident(self.ident_in_2)
            self.selected <<= Fn.select(self.sel_bit, self.ident_in, self.ident_in_2)
            self.selected_2 <<= Fn.select_nested(
                self.sel_bit, self.ident_in, self.ident_in_2
            )
            self.selected_nullfull <<= Fn.select_nested(self.sel_bit, Full, Null)


#
# test code
#


@cocotb_util.test()
async def testbench_functions(dut: test_functions):
    ident_gen = cocotb_util.ConstrainedGenerator(4)
    sel_gen = cocotb_util.ConstrainedGenerator(1)
    nullfull_gen = cocotb_util.ConstrainedGenerator(4)

    for ident in ident_gen.all():
        for ident_2 in ident_gen.all():
            for sel_bit in sel_gen.all():
                check_msg = f"{ident=}, {ident_2=}, {sel_bit=}"
                nullfull = nullfull_gen.full() if sel_bit else nullfull_gen.null()

                await cocotb_util.check_concurrent(
                    [
                        (dut.ident_in, ident),
                        (dut.ident_in_2, ident_2),
                        (dut.sel_bit, sel_bit),
                    ],
                    [
                        (dut.ident_out, ident),
                        (dut.ident_out_2, ident_2),
                        (dut.selected, ident if sel_bit == "1" else ident_2),
                        (dut.selected_2, ident if sel_bit == "1" else ident_2),
                        (dut.selected_nullfull, nullfull),
                    ],
                    check_msg=check_msg,
                )


class Unittest(unittest.TestCase):
    def test_functions(self):
        cocotb_util.run_cocotb_tests(test_functions, __file__, self.__module__)
