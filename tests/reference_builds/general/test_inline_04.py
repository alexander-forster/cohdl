from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, Port, BitVector
from cohdl import std

from cohdl_testutil import cocotb_util

from cohdl import vhdl, inline_raw

inline_hint = None


def gen_entity():
    class test_inline_04(cohdl.Entity):
        inp_bit_1 = Port.input(Bit)
        inp_bit_2 = Port.input(Bit)
        inp_bit_3 = Port.input(Bit)
        inp_bit_4 = Port.input(Bit)

        out_side_effect_1 = Port.output(Bit)
        out_side_effect_2 = Port.output(Bit)
        out_side_effect_3 = Port.output(Bit)

        out_1 = Port.output(Bit)
        out_2 = Port.output(Bit)
        out_3 = Port.output(Bit)
        out_4 = Port.output(BitVector[2])

        def architecture(self):
            def and_cohdl(a, b):
                return a & b

            def and_op(a, b):
                return f"{vhdl:{a!r} and {b!r}}"

            @std.concurrent
            def logic():

                def assign_to(a, b):
                    a <<= b

                hdl_dict = {
                    "concat": f"{inline_hint[BitVector[2]]:({self.inp_bit_1!r} & {self.inp_bit_3!r})}",
                    "expr": f"{inline_hint[Bit]:({self.inp_bit_2!r} and {self.inp_bit_3!r}); --UNUSED-EXPR-IN-HDL--}",
                    "or": f"{inline_hint[Bit]:({self.inp_bit_4!r} or {self.inp_bit_3!r})}",
                    "stmt": f"{inline_hint:({self.inp_bit_2!r} and {self.inp_bit_3!r}) --UNUSED-STMT-NOT-IN-HDL--}",
                }

                expr = f"{inline_hint[Bit]:({self.inp_bit_2!r}); --UNUSED-EXPR-IN-HDL-2-- {assign_to(self.out_side_effect_2, f'{vhdl[Bit]:{and_op(self.inp_bit_1, self.inp_bit_4)}}')}}"
                stmt = f"{inline_hint:({self.inp_bit_2!r}) --UNUSED-STMT-NOT-IN-HDL-- {assign_to(self.out_side_effect_3, and_cohdl(self.inp_bit_1, self.inp_bit_2))}}"

                xor_12 = f"{inline_hint[Bit]:({self.inp_bit_1!r} xor {self.inp_bit_2!r}); -- {assign_to(self.out_side_effect_1, self.inp_bit_1)}}"

                self.out_1 <<= f"{inline_hint[Bit]:({xor_12!r})}"
                self.out_2 <<= xor_12
                self.out_3 <<= hdl_dict["or"]
                self.out_4 <<= hdl_dict["concat"]

    return test_inline_04


#
# test code
#


@cocotb_util.test()
async def testbench_match_simple(dut):
    inp_1_gen = cocotb_util.ConstrainedGenerator(1)
    inp_2_gen = cocotb_util.ConstrainedGenerator(1)
    inp_3_gen = cocotb_util.ConstrainedGenerator(1)
    inp_4_gen = cocotb_util.ConstrainedGenerator(1)

    for inp_1 in inp_1_gen.all():
        for inp_2 in inp_2_gen.all():
            for inp_3 in inp_3_gen.all():
                for inp_4 in inp_4_gen.all():

                    bv_result = (inp_1.as_int() << 1) | inp_3.as_int()

                    await cocotb_util.check_concurrent(
                        [
                            (dut.inp_bit_1, inp_1),
                            (dut.inp_bit_2, inp_2),
                            (dut.inp_bit_3, inp_3),
                            (dut.inp_bit_4, inp_4),
                        ],
                        [
                            (dut.out_1, inp_1 ^ inp_2),
                            (dut.out_2, inp_1 ^ inp_2),
                            (dut.out_3, inp_4 | inp_3),
                            (dut.out_4, bv_result),
                            (dut.out_side_effect_1, inp_1),
                            (dut.out_side_effect_2, inp_1 & inp_4),
                            (dut.out_side_effect_3, inp_1 & inp_2),
                        ],
                        check_msg=f"{inp_1=}, {inp_3=}, {bv_result=}",
                    )


class Unittest(unittest.TestCase):
    # check nested inline HDL

    def test_inline(self):
        global inline_hint
        inline_hint = inline_raw
        cocotb_util.run_cocotb_tests(gen_entity(), __file__, self.__module__)

    def test_inline_vhdl(self):
        global inline_hint
        inline_hint = vhdl
        cocotb_util.run_cocotb_tests(gen_entity(), __file__, self.__module__)

    def test_unused_gen(self):
        global inline_hint
        inline_hint = vhdl

        hdl = std.VhdlCompiler.to_string(gen_entity())

        assert "--UNUSED-EXPR-IN-HDL--" in hdl
        assert "--UNUSED-EXPR-IN-HDL-2--" in hdl
        assert "--UNUSED-STMT-NOT-IN-HDL--" not in hdl
        assert "--UNUSED-STMT-NOT-IN-HDL--" not in hdl
