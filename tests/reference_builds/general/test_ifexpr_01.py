from __future__ import annotations

from typing import Any, Tuple
import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Unsigned, Signed, Null, Full, enum

from cohdl import std

from cohdl_testutil import cocotb_util


def choose_first(options: list[Tuple[Any, Any]], default):
    if len(options) == 0:
        return default
    else:
        value, cond = options[0]
        rest = options[1:]
        return value if cond else choose_first(rest, default)


class test_if_expr(cohdl.Entity):
    sw = Port.input(BitVector[4])

    ifexpr_bit = Port.output(Bit)
    ifexpr_bitvector = Port.output(BitVector[4])
    ifexpr_signed = Port.output(Signed[4])
    ifexpr_unsigned = Port.output(Unsigned[4])
    ifexpr_bitvector_signal = Port.output(BitVector[4])

    option_a = Port.input(BitVector[2])
    option_b = Port.input(BitVector[2])

    choose_bit = Port.output(Bit)
    choose_bit_2 = Port.output(Bit)
    choose_bit_3 = Port.output(Bit)

    choose_unsigned = Port.output(Unsigned[4])
    choose_unsigned_2 = Port.output(Unsigned[4])
    choose_unsigned_3 = Port.output(Unsigned[4])

    choose_pos_a = Port.output(Unsigned[4])
    choose_option = Port.output(BitVector[2])

    def architecture(self):
        @std.concurrent
        def logic_ifexpr():
            self.ifexpr_bit <<= "1" if self.sw[0] == self.sw[1] else "0"
            self.ifexpr_bitvector <<= (
                "1000"
                if self.sw[0] == self.sw[1]
                else "0001"
                if self.sw[1] == self.sw[2]
                else Null
            )

            self.ifexpr_bitvector_signal <<= (
                self.sw
                if self.sw[0] == self.sw[1]
                else ~self.sw
                if self.sw[1] == self.sw[2]
                else Full
            )

            self.ifexpr_unsigned <<= (
                1 if self.sw[0] == self.sw[1] else 2 if self.sw[1] == self.sw[2] else 0
            )

            self.ifexpr_signed <<= (
                -1
                if self.sw[0] == self.sw[1]
                else -2
                if self.sw[1] == self.sw[2]
                else -3
                if self.sw[2] == self.sw[3]
                else 0
            )

        @std.concurrent
        def logic_choose():
            self.choose_bit <<= choose_first([("1", self.sw[0])], self.sw[2])

            self.choose_bit_2 <<= choose_first(
                [
                    ("1", self.sw[1:0] == self.option_a),
                    ("0", self.sw[1:0] == self.option_b),
                ],
                self.sw[2],
            )

            self.choose_bit_3 <<= choose_first(
                [
                    ("1", self.sw[1:0] == self.option_a),
                    ("0", self.sw[1:0] == self.option_b),
                    ("1", self.sw[2:1] == self.option_a),
                ],
                self.sw[2],
            )

            # find first set
            self.choose_unsigned <<= choose_first(
                [
                    (1, self.sw[0]),
                    (2, self.sw[1]),
                    (3, self.sw[2]),
                    (4, self.sw[3]),
                ],
                0,
            )

            self.choose_unsigned_2 <<= choose_first(
                [(nr + 1, bit) for nr, bit in enumerate(self.sw)],
                0,
            )

            # find first zero
            self.choose_unsigned_3 <<= choose_first(
                [(nr + 1, ~bit) for nr, bit in enumerate(self.sw)],
                0,
            )

            self.choose_pos_a <<= choose_first(
                [
                    (nr + 1, self.option_a == b @ a)
                    for nr, (a, b) in enumerate(zip(self.sw, self.sw.msb(rest=1)))
                ],
                0,
            )

            self.choose_option <<= choose_first(
                [
                    (self.option_a if self.sw[0] == bit else self.option_b, bit)
                    for bit in self.sw
                ],
                Null,
            )


#
# test code
#


def bin_str(val: int, len):
    return ("0" * len + bin(val)[2:])[-len:]


@cocotb_util.test()
async def testbench_ifexpr(dut: test_if_expr):
    await cocotb_util.check_concurrent(
        [(dut.sw, "0000")],
        [
            (dut.ifexpr_bit, 1),
            (dut.ifexpr_bitvector, "1000"),
            (dut.ifexpr_bitvector_signal, "0000"),
            (dut.ifexpr_unsigned, 1),
            (dut.ifexpr_signed, -1),
        ],
    )

    await cocotb_util.check_concurrent(
        [(dut.sw, "0001")],
        [
            (dut.ifexpr_bit, 0),
            (dut.ifexpr_bitvector, "0001"),
            (dut.ifexpr_bitvector_signal, "1110"),
            (dut.ifexpr_unsigned, 2),
            (dut.ifexpr_signed, -2),
        ],
    )

    await cocotb_util.check_concurrent(
        [(dut.sw, "0010")],
        [
            (dut.ifexpr_bit, 0),
            (dut.ifexpr_bitvector, "0000"),
            (dut.ifexpr_bitvector_signal, "1111"),
            (dut.ifexpr_unsigned, 0),
            (dut.ifexpr_signed, -3),
        ],
    )

    await cocotb_util.check_concurrent(
        [(dut.sw, "0011")],
        [
            (dut.ifexpr_bit, 1),
            (dut.ifexpr_bitvector, "1000"),
            (dut.ifexpr_bitvector_signal, "0011"),
            (dut.ifexpr_unsigned, 1),
            (dut.ifexpr_signed, -1),
        ],
    )

    await cocotb_util.check_concurrent(
        [(dut.sw, "0100")],
        [
            (dut.ifexpr_bit, 1),
            (dut.ifexpr_bitvector, "1000"),
            (dut.ifexpr_bitvector_signal, "0100"),
            (dut.ifexpr_unsigned, 1),
            (dut.ifexpr_signed, -1),
        ],
    )


@cocotb_util.test()
async def testbench_choose(dut: test_if_expr):
    sw_gen = cocotb_util.ConstrainedGenerator(4)
    option_gen = cocotb_util.ConstrainedGenerator(2)

    for sw in sw_gen.all():
        for a in option_gen.all():
            for b in option_gen.all():
                msg = (f"{sw=}, {a=}, {b=}",)

                await cocotb_util.check_concurrent(
                    [
                        (dut.sw, sw),
                        (dut.option_a, a),
                        (dut.option_b, b),
                    ],
                    [
                        (
                            dut.choose_bit,
                            1 if sw[0] else sw[2],
                            f"dut.choose_bit ::   {msg}",
                        ),
                        (
                            dut.choose_bit_2,
                            1 if sw[0:1] == a else 0 if sw[0:1] == b else sw[2],
                            f"dut.choose_bit_2 ::  {sw[0:1]} {msg}",
                        ),
                        (
                            dut.choose_bit_3,
                            1
                            if sw[0:1] == a
                            else 0
                            if sw[0:1] == b
                            else 1
                            if sw[1:2] == a
                            else sw[2],
                            f"dut.choose_bit_3 ::   {msg}",
                        ),
                        (
                            # find first '1'
                            dut.choose_unsigned,
                            1
                            if sw[0]
                            else 2
                            if sw[1]
                            else 3
                            if sw[2]
                            else 4
                            if sw[3]
                            else 0,
                            f"dut.choose_unsigned ::   {msg}",
                        ),
                        (
                            # find first '1'
                            dut.choose_unsigned_2,
                            1
                            if sw[0]
                            else 2
                            if sw[1]
                            else 3
                            if sw[2]
                            else 4
                            if sw[3]
                            else 0,
                            f"dut.choose_unsigned_2 ::   {msg}",
                        ),
                        (
                            # find first '0'
                            dut.choose_unsigned_3,
                            1
                            if ~sw[0]
                            else 2
                            if ~sw[1]
                            else 3
                            if ~sw[2]
                            else 4
                            if ~sw[3]
                            else 0,
                            f"dut.choose_unsigned_3 ::   {msg}",
                        ),
                        (
                            dut.choose_pos_a,
                            1
                            if sw[0:1] == a
                            else 2
                            if sw[1:2] == a
                            else 3
                            if sw[2:3] == a
                            else 0,
                            f"dut.choose_pos_a ::   {msg}",
                        ),
                        (
                            dut.choose_option,
                            (
                                [a if sw[0] == bit else b for bit in sw if bit == "1"]
                                + [0]
                            )[0],
                            f"dut.choose_option ::   {msg}",
                        ),
                    ],
                )


class Unittest(unittest.TestCase):
    def test_if_expr(self):
        cocotb_util.run_cocotb_tests(test_if_expr, __file__, self.__module__)
