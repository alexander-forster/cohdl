from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Signal, Array

from cohdl import std

from cohdl_testutil import cocotb_util


class test_array_01(cohdl.Entity):
    clk = Port.input(Bit)
    rd_addr = Port.input(BitVector[4])
    rd_data = Port.output(BitVector[16])

    wr_addr = Port.input(BitVector[4])
    wr_data = Port.input(BitVector[16])

    def architecture(self):
        mem = Signal[Array[BitVector[16], 16]]()

        @std.sequential(std.Clock(self.clk))
        def proc():
            self.rd_data <<= mem[self.rd_addr.unsigned]
            mem[self.wr_addr.unsigned] <<= self.wr_data


#
# test code
#


@cocotb_util.test()
async def testbench_functions(dut: test_array_01):
    seq_test = cocotb_util.SequentialTest(dut.clk)

    data_gen = cocotb_util.ConstrainedGenerator(16)
    addr_gen = cocotb_util.ConstrainedGenerator(4)

    memory = [0] * 16
    await seq_test.tick()

    for addr in addr_gen.all():
        value = data_gen.random()
        memory[addr.as_int()] = value

        cocotb_util.assign(dut.wr_data, value)
        cocotb_util.assign(dut.rd_addr, addr)
        cocotb_util.assign(dut.wr_addr, addr)

        await seq_test.tick()
        await seq_test.tick()

        assert cocotb_util.compare(dut.rd_data, value)

    for rd_addr, wr_addr, data in zip(
        addr_gen.random(128), addr_gen.random(128), data_gen.random(128)
    ):
        cocotb_util.assign(dut.wr_addr, wr_addr)
        cocotb_util.assign(dut.rd_addr, rd_addr)
        cocotb_util.assign(dut.wr_data, data)
        memory[wr_addr.as_int()] = data

        await seq_test.tick()
        await seq_test.tick()

        assert cocotb_util.compare(dut.rd_data, memory[rd_addr.as_int()])


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(
            test_array_01,
            __file__,
            self.__module__,
        )
