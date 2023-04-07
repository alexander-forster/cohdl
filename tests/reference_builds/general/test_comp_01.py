from __future__ import annotations

import unittest

import itertools

import cohdl
from cohdl import Bit, BitVector, Unsigned, Port, select_with
from cohdl import std

from cohdl_testutil import cocotb_util

context = None


def gen_entity():
    class test_comp_01(cohdl.Entity):
        inp_a = Port.input(Bit)
        inp_b = Port.input(Bit)
        inp_c = Port.input(Bit)

        inp_selector = Port.input(Unsigned[4])
        out_selected = Port.output(Bit)

        inp_wide = Port.input(BitVector[4])
        out_narrow = Port.output(BitVector[2])

        def architecture(self):
            l = [self.inp_a, self.inp_b, self.inp_c]

            @context
            def logic():
                s = {key: value for key, value in enumerate(l)}

                self.out_selected <<= select_with(
                    self.inp_selector,
                    s,
                    0,
                )

                inp_narrow = [
                    self.inp_wide[nr] for nr in range(0, self.inp_wide.width, 2)
                ]

                for bit_inp, bit_out in zip(inp_narrow, self.out_narrow):
                    bit_out <<= bit_inp

    return test_comp_01


#
# test code
#


@cocotb_util.test()
async def testbench_comp_01(dut):
    ConstrainedGenerator = cocotb_util.ConstrainedGenerator
    cv = cocotb_util.ConstraindValue
    bit_generator = ConstrainedGenerator(1)
    bv_generator = ConstrainedGenerator(4)

    for a, b, c, sel in itertools.product(
        bit_generator.all(),
        bit_generator.all(),
        bit_generator.all(),
        bv_generator.all(),
    ):
        s = sel.value

        selected = {0: a, 1: b, 2: c}.get(s, 0)

        wide = sel
        narrow = cv(2, sel[0]) | cv(2, (sel[2].as_int() << 1))

        await cocotb_util.check_concurrent(
            [
                (dut.inp_a, a),
                (dut.inp_b, b),
                (dut.inp_c, c),
                (
                    dut.inp_selector,
                    sel,
                ),
                (dut.inp_wide, wide),
            ],
            [
                (dut.out_selected, selected),
                (dut.out_narrow, narrow),
            ],
        )

        #


class Unittest(unittest.TestCase):
    def test_concurrent(self):
        global context
        context = std.concurrent
        cocotb_util.run_cocotb_tests(gen_entity(), __file__, self.__module__)

    def test_sequential(self):
        global context
        context = std.sequential
        cocotb_util.run_cocotb_tests(gen_entity(), __file__, self.__module__)
