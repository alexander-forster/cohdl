from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Unsigned, Signed, select_with, Null, Full

from cohdl import std

from cohdl_testutil import cocotb_util


class test_select_with(cohdl.Entity):
    sw = Port.input(BitVector[4])

    sel_bit = Port.output(Bit)
    sel_bitvector = Port.output(BitVector[4])
    sel_signed = Port.output(Signed[4])
    sel_unsigned = Port.output(Unsigned[4])
    sel_bitvector_signal = Port.output(BitVector[4])

    sel_nested = Port.output(BitVector[4])

    test_inp = Port.input(BitVector[4])
    test_out = Port.output(BitVector[4])

    def architecture(self):
        @std.concurrent
        def logic_select_with():
            self.test_out <<= self.test_inp
            self.sel_bit <<= select_with(self.sw[0], {"0": "1", "1": "0"}, default="0")

            self.sel_bitvector <<= select_with(
                self.sw[1:0],
                {"01": "0011", "10": "1100"},
                default="0000",
            )

            self.sel_bitvector_signal <<= select_with(
                self.sw[1:0],
                {"00": "1111", "01": self.sw, "10": ~self.sw},
                default="0000",
            )

            self.sel_unsigned <<= select_with(
                self.sw[1:0],
                {"00": 4, "01": 3, "10": 2, "11": 1},
                default=0,
            )

            self.sel_signed <<= select_with(
                self.sw[1:0],
                {"00": -2, "01": -1, "10": 1, "11": 2},
                default=0,
            )

        @std.concurrent
        def logic_select_nested():
            self.sel_nested <<= select_with(
                self.sw[1:0],
                {
                    "00": self.sw if self.sw.msb() else Full,
                    "01": "1011",
                    "10": select_with(
                        self.sw.msb(),
                        {
                            "0": self.sw,
                            "1": ~self.sw,
                        },
                        default=Full,
                    ),
                },
                default=Null,
            )


#
# test code
#


@cocotb_util.test()
async def testbench_select_with(dut: test_select_with):
    await cocotb_util.check_concurrent(
        [(dut.sw, "0000")],
        [
            (dut.sel_bit, 1),
            (dut.sel_bitvector, 0),
            (dut.sel_bitvector_signal, "1111"),
            (dut.sel_unsigned, 4),
            (dut.sel_signed, -2),
        ],
    )

    await cocotb_util.check_concurrent(
        [(dut.sw, "0001")],
        [
            (dut.sel_bit, 0),
            (dut.sel_bitvector, "0011"),
            (dut.sel_bitvector_signal, dut.sw),
            (dut.sel_unsigned, 3),
            (dut.sel_signed, -1),
        ],
    )

    await cocotb_util.check_concurrent(
        [(dut.sw, "0010")],
        [
            (dut.sel_bit, 1),
            (dut.sel_bitvector, "1100"),
            (dut.sel_bitvector_signal, "1101"),
            (dut.sel_unsigned, 2),
            (dut.sel_signed, 1),
        ],
    )

    await cocotb_util.check_concurrent(
        [(dut.sw, "0011")],
        [
            (dut.sel_bit, 0),
            (dut.sel_bitvector, "0000"),
            (dut.sel_bitvector_signal, 0),
            (dut.sel_unsigned, 1),
            (dut.sel_signed, 2),
        ],
    )


@cocotb_util.test()
async def testbench_select_nested(dut: test_select_with):
    sw_gen = cocotb_util.ConstrainedGenerator(4)

    def select_nested(sw: cocotb_util.ConstraindValue):
        match sw.get_slice(0, 1).as_str():
            case "00":
                return sw if sw.get_bit(-1) else "1111"
            case "01":
                return "1011"
            case "10":
                if ~sw.get_bit(-1):
                    return sw
                else:
                    return ~sw
            case _:
                return "0000"

    for sw in sw_gen.all():
        await cocotb_util.check_concurrent(
            [
                (dut.sw, sw),
                (dut.test_inp, sw),
            ],
            [
                (dut.sel_nested, select_nested(sw)),
                (dut.test_out, sw),
            ],
        )


class Unittest(unittest.TestCase):
    def test_select_with(self):
        cocotb_util.run_cocotb_tests(test_select_with, __file__, self.__module__)
