from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port
from cohdl import std

from cohdl_testutil import cocotb_util

from cohdl import vhdl, inline_raw

inline_hint = None


def gen_entity():
    class test_inline_02(cohdl.Entity):
        inp_bit_1 = Port.input(Bit)
        inp_bit_2 = Port.input(Bit)

        out_bit = Port.output(Bit)

        def architecture(self):
            @std.concurrent
            def logic():
                self.out_bit <<= (
                    f"{inline_hint[Bit]:{self.inp_bit_1!r} or {self.inp_bit_2!r}}"
                )

    return test_inline_02


#
# test code
#


@cocotb_util.test()
async def testbench_match_simple(dut):
    inp_1_gen = cocotb_util.ConstrainedGenerator(1)
    inp_2_gen = cocotb_util.ConstrainedGenerator(1)

    for inp_1 in inp_1_gen.all():
        for inp_2 in inp_2_gen.all():
            out_bit = inp_1 | inp_2

            await cocotb_util.check_concurrent(
                [(dut.inp_bit_1, inp_1), (dut.inp_bit_2, inp_2)],
                [
                    (dut.out_bit, out_bit),
                ],
                check_msg=f"{inp_1=}, {inp_2=}",
            )


class Unittest(unittest.TestCase):
    def test_inline(self):
        global inline_hint
        inline_hint = inline_raw
        cocotb_util.run_cocotb_tests(gen_entity(), __file__, self.__module__)

    def test_inline_vhdl(self):
        global inline_hint
        inline_hint = vhdl
        cocotb_util.run_cocotb_tests(gen_entity(), __file__, self.__module__)
