from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Unsigned, Signed, select_with, Null, Full

from cohdl import std

from cohdl_testutil import cocotb_util

ctx_type = None
sw_type = None

# compile feedback used to test that
# entity instances are not cached between builds
compile_feedback = None


class test_select_with(cohdl.Entity):
    sw = Port.input(BitVector[4])
    sw_u = Port.input(Unsigned[4])
    sw_s = Port.input(Signed[4])

    test_inp = Port.input(BitVector[8])

    sel_a = Port.output(Bit)
    sel_b = Port.output(BitVector[2])
    sel_c = Port.output(BitVector[4])
    sel_d = Port.output(Unsigned[3])

    def architecture(self):

        if sw_type is BitVector:
            sw = self.sw
        elif sw_type is Unsigned:
            sw = self.sw_u
        elif sw_type is Signed:
            sw = self.sw_s
        else:
            raise AssertionError(f"invalid sw_type {sw_type}")

        global compile_feedback

        compile_feedback = (ctx_type, sw_type)

        @ctx_type
        def logic_select_with():
            self.sel_a <<= select_with(
                sw[0],
                {
                    "0": "1",
                    True: Bit(0),
                },
                default=Null,
            )

            self.sel_b <<= select_with(
                sw[1:0].unsigned,
                {
                    0: "01",
                    Unsigned[1](1): self.test_inp[5:4],
                    BitVector[2]("10"): Full,
                },
                default=self.test_inp[7:6],
            )

            self.sel_c <<= select_with(
                sw.signed,
                {
                    -3: Full,
                    5: Unsigned[4](5),
                    Signed[2](1): self.test_inp[7:4],
                    Full: self.test_inp[5:2],
                    Unsigned[3](7): self.test_inp[6:3].signed,
                },
                default=Full,
            )


#
# test code
#


@cocotb_util.test()
async def testbench_select_with(dut: test_select_with):
    gen = cocotb_util.ConstrainedGenerator(8)

    for sw in range(16):

        for test_inp in gen.random(4):

            sel_a = 0 if sw & 1 else 1

            await cocotb_util.check_concurrent(
                [
                    (dut.sw, sw),
                    (dut.sw_s, sw),
                    (dut.sw_u, sw),
                    (dut.test_inp, test_inp),
                ],
                [
                    (dut.sel_a, sel_a),
                ],
            )


class Unittest(unittest.TestCase):
    def test_select_with(self):
        global ctx_type, sw_type

        for ctx in (std.concurrent, std.sequential):
            for sw in (BitVector, Unsigned, Signed):
                ctx_type = ctx
                sw_type = sw

                cocotb_util.run_cocotb_tests(
                    test_select_with, __file__, self.__module__
                )

                assert compile_feedback[0] is ctx
                assert compile_feedback[1] is sw
