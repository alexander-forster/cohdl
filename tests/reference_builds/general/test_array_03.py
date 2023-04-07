from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Signal, Array, Unsigned

from cohdl import std

from cohdl_testutil import cocotb_util


class test_array_03(cohdl.Entity):
    clk = Port.input(Bit)

    rd_addr = Port.input(Unsigned[2])
    rd_data = Port.output(BitVector[4])

    def architecture(self):
        mem = Signal[Array[BitVector[4], 4]](["0000", "0110", "1010", "1100"])

        @std.concurrent
        def proc():
            self.rd_data <<= mem[self.rd_addr]


#
# test code
#


@cocotb_util.test()
async def testbench_functions(dut: test_array_03):

    addr_gen = cocotb_util.ConstrainedGenerator(2)

    memory = ["0000", "0110", "1010", "1100"]

    for addr in addr_gen.all():
        await cocotb_util.check_concurrent(
            [(dut.rd_addr, addr)],
            [(dut.rd_data, memory[addr.as_int()])],
        )


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_array_03, __file__, self.__module__)
