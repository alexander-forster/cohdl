from __future__ import annotations

import unittest

import cohdl
from cohdl import (
    std,
    BitVector,
    Unsigned,
    Signed,
    Port,
)

from cohdl_testutil import cocotb_util
import random
import os

INP_W = eval(os.getenv("cohdl_test_inp_width", "8"))
INP_TYPE = eval(os.getenv("cohdl_test_inp_type", "BitVector"))[INP_W]


def gen_dut(ctx_type):
    class test_leading_trailing(cohdl.Entity):

        input = Port.input(INP_TYPE)

        leading_0 = Port.output(Unsigned.upto(INP_W))
        leading_1 = Port.output(Unsigned.upto(INP_W))
        trailing_0 = Port.output(Unsigned.upto(INP_W))
        trailing_1 = Port.output(Unsigned.upto(INP_W))

        def architecture(self):

            @ctx_type
            def logic_assign():
                self.leading_0 <<= std.count_leading_zeros(self.input)
                self.leading_1 <<= std.count_leading_ones(self.input)
                self.trailing_0 <<= std.count_trailing_zeros(self.input)
                self.trailing_1 <<= std.count_trailing_ones(self.input)

    return test_leading_trailing


#
# test code
#


def count_values(val: int, width: int):

    if val < 0:
        val += 2 ** (width - 1)

    s = f"{val:0{width}b}"

    leading_zeros = (s + "1").index("1")
    leading_ones = (s + "0").index("0")

    trailing_zeros = width - ("1" + s).rindex("1")
    trailing_ones = width - ("0" + s).rindex("0")

    return leading_zeros, leading_ones, trailing_zeros, trailing_ones


@cocotb_util.test()
async def testbench_leading_trailing(dut):
    for _ in range(64):
        inp_val = random.randint(0, 2**INP_W - 1)

        dut.input.value = inp_val

        await cocotb_util.step()

        lz, lo, tz, to = count_values(inp_val, INP_W)

        assert lz == dut.leading_0.value
        assert lo == dut.leading_1.value
        assert tz == dut.trailing_0.value
        assert to == dut.trailing_1.value


class Unittest(unittest.TestCase):
    def test_hdl(self):
        global INP_W, INP_TYPE

        for ctx_type in (std.concurrent, std.sequential):
            for w in (1, 2, 10):
                INP_W = w

                for vec_type in ("BitVector", "Signed", "Unsigned"):
                    INP_TYPE = eval(vec_type)[w]

                    cocotb_util.run_cocotb_tests(
                        gen_dut(ctx_type),
                        __file__,
                        self.__module__,
                        extra_env={
                            "cohdl_test_inp_type": vec_type,
                            "cohdl_test_inp_width": repr(w),
                        },
                    )

    def test_python(self):

        for w in (1, 2, 3, 5, 10):
            for VecType in (BitVector, Signed, Unsigned):
                for _ in range(64):
                    inp_val = random.randint(0, 2**w - 1)
                    val = VecType[w](Unsigned[w](inp_val).bitvector)

                    lz, lo, tz, to = count_values(inp_val, w)

                    assert lz == std.count_leading_zeros(val)
                    assert lo == std.count_leading_ones(val)
                    assert tz == std.count_trailing_zeros(val)
                    assert to == std.count_trailing_ones(val)
