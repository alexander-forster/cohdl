from __future__ import annotations

import unittest

import cohdl
from cohdl import std, BitVector, Unsigned, Port, Bit

from cohdl_testutil import cocotb_util
import random


def gen_dut(ctx_type):
    class test_count_elements(cohdl.Entity):

        input = Port.input(BitVector[8])

        inp_until_0 = Port.output(Unsigned.upto(8))
        list_until_1 = Port.output(Unsigned.upto(8))
        inp_until_not0 = Port.output(Unsigned.upto(8))
        list_until_not1 = Port.output(Unsigned.upto(8))

        inp_while_0 = Port.output(Unsigned.upto(8))
        list_while_1 = Port.output(Unsigned.upto(8))
        inp_while_not0 = Port.output(Unsigned.upto(8))
        list_while_not1 = Port.output(Unsigned.upto(8))

        empty_until_val = Port.output(Unsigned.upto(0))
        empty_until_cond = Port.output(Unsigned.upto(0))
        empty_while_val = Port.output(Unsigned.upto(0))
        empty_while_cond = Port.output(Unsigned.upto(0))

        def architecture(self):
            inp_list = [*self.input]

            @ctx_type
            def logic_assign():
                self.inp_until_0 <<= std.count_elements_until(self.input, Bit(0))
                self.list_until_1 <<= std.count_elements_until(inp_list, Bit(1))

                self.inp_until_not0 <<= std.count_elements_until(
                    self.input, cond=lambda x: x != Bit(0)
                )
                self.list_until_not1 <<= std.count_elements_until(
                    inp_list, cond=lambda x: x != Bit(1)
                )

                self.inp_while_0 <<= std.count_elements_while(self.input, Bit(0))
                self.list_while_1 <<= std.count_elements_while(inp_list, Bit(1))

                self.inp_while_not0 <<= std.count_elements_while(
                    self.input, cond=lambda x: x != Bit(0)
                )
                self.list_while_not1 <<= std.count_elements_while(
                    inp_list, cond=lambda x: x != Bit(1)
                )

                self.empty_until_val <<= std.count_elements_until((), "asdf")
                self.empty_until_cond <<= std.count_elements_until(
                    {}, cond=lambda x: False
                )
                self.empty_while_val <<= std.count_elements_while((), "asdf")
                self.empty_while_cond <<= std.count_elements_while(
                    {}, cond=lambda x: False
                )

    return test_count_elements


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
async def testbench_count_elements(dut):
    for _ in range(64):
        inp_val = random.randint(0, 2**8 - 1)
        dut.input.value = inp_val

        await cocotb_util.step()

        lz, lo, tz, to = count_values(inp_val, 8)

        assert dut.inp_until_0.value == to
        assert dut.list_until_1.value == tz
        assert dut.inp_until_not0.value == tz
        assert dut.list_until_not1.value == to

        assert dut.inp_while_0.value == tz
        assert dut.list_while_1.value == to
        assert dut.inp_while_not0.value == to
        assert dut.list_while_not1.value == tz

        assert dut.empty_until_val.value == 0
        assert dut.empty_until_cond.value == 0
        assert dut.empty_while_val.value == 0
        assert dut.empty_while_cond.value == 0


class Unittest(unittest.TestCase):
    def test_hdl(self):
        for ctx_type in (std.concurrent, std.sequential):
            cocotb_util.run_cocotb_tests(gen_dut(ctx_type), __file__, self.__module__)

    def test_python(self):

        assert std.count_elements_while([], None) == 0
        assert std.count_elements_while((), None) == 0
        assert std.count_elements_until({}, None) == 0
        assert std.count_elements_until(set(), None) == 0

        assert std.count_elements_while((1, 1, 2), 1) == 2
        assert std.count_elements_while((3, 1, 2), 1) == 0
        assert (
            std.count_elements_while((3, 1, 2, -9, 333, 555), cond=lambda x: x != 555)
            == 5
        )

        assert std.count_elements_until((1, 1, 2), 1) == 0
        assert std.count_elements_until((3, 1, 2), 1) == 1
        assert (
            std.count_elements_until((3, 1, 2, -9, 333, 555), cond=lambda x: x == 333)
            == 4
        )

        # check that only one argument can be passed to the count_elements functions
        self.assertRaises(TypeError, std.count_elements_while, (), None, None)
        self.assertRaises(TypeError, std.count_elements_until, (), None, None)
        self.assertRaises(AssertionError, std.count_elements_while, (), None, cond=None)
        self.assertRaises(AssertionError, std.count_elements_until, (), None, cond=None)
