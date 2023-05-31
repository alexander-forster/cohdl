from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Signal, Array, Unsigned

from cohdl import std

from cohdl_testutil import cocotb_util


class test_array_05(cohdl.Entity):
    clk = Port.input(Bit)
    reset = Port.input(Bit)

    choose_option = Port.input(Bit)

    rd_data = Port.output(BitVector[4])

    def architecture(self):
        default = Array[BitVector[4], 1](["0000"])
        option_a = Array[BitVector[4], 1](["1100"])
        option_b = Array[BitVector[4], 1](["1111"])

        mem = Signal[Array[BitVector[4], 1]](default)

        @std.concurrent
        def logic():
            self.rd_data <<= mem[0]

        @std.sequential(std.Clock(self.clk), std.Reset(self.reset))
        def proc():
            if self.choose_option:
                mem.next = option_a
            else:
                mem.next = option_b


#
# test code
#


@cocotb_util.test()
async def testbench_functions(dut: test_array_05):
    seq = cocotb_util.SequentialTest(dut.clk)

    bit_gen = cocotb_util.ConstrainedGenerator(1)

    default = ["0000"]
    option_a = ["1100"]
    option_b = ["1111"]

    for addr in [0, 0, 0, 0]:
        reset = bit_gen.random()
        choose = bit_gen.random()

        if not reset:
            if choose:
                expected = option_a[addr]
            else:
                expected = option_b[addr]
        else:
            expected = default[addr]

        await seq.check_next_tick(
            [
                (dut.reset, reset),
                (dut.choose_option, choose),
            ],
            [
                (dut.rd_data, expected),
            ],
        )


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_array_05, __file__, self.__module__)
