from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port
from cohdl import std

from cohdl_testutil import cocotb_util

from cohdl import vhdl, inline_raw


inline_hint = None


def gen_entity():
    class test_inline_01(cohdl.Entity):
        inp_1 = Port.input(Bit)
        inp_2 = Port.input(BitVector[4])

        out_1 = Port.output(Bit)
        out_2 = Port.output(BitVector[4])
        out_3 = Port.output(Bit)
        out_4 = Port.output(BitVector[4])

        def architecture(self):
            @std.concurrent
            def logic():
                f"{inline_hint:{self.out_1} <= {self.inp_1!r};}"
                f"{inline_hint:{self.out_2} <= {self.inp_2!r};}"
                f"{inline_hint:{self.out_3} <= {self.inp_2!r}(0);}"

                f"{inline_hint:{self.out_4[0]} <= {self.inp_2[0]!r};}"
                f"{inline_hint:{self.out_4}(1) <= {self.inp_2[1]!r};}"
                f"{inline_hint:{self.out_4[2]} <= {self.inp_2!r}(2);}"
                f"{inline_hint:{self.out_4}(3) <= {self.inp_2!r}(3);}"

    return test_inline_01


#
# test code
#


@cocotb_util.test()
async def testbench_match_simple(dut):
    inp_1_gen = cocotb_util.ConstrainedGenerator(1)
    inp_2_gen = cocotb_util.ConstrainedGenerator(4)

    for inp_1 in inp_1_gen.all():
        for inp_2 in inp_2_gen.all():
            await cocotb_util.check_concurrent(
                [(dut.inp_1, inp_1), (dut.inp_2, inp_2)],
                [
                    (dut.out_1, inp_1),
                    (dut.out_2, inp_2),
                    (dut.out_3, inp_2.get_bit(0)),
                    (dut.out_4, inp_2),
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
