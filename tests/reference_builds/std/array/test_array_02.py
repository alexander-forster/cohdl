from __future__ import annotations

import unittest

import cohdl
from cohdl import std, Bit, BitVector, Port, Unsigned, Signed, Null

import cohdl_testutil

from cohdl_testutil import cocotb_util
from cohdl_testutil.cocotb_mock import MockBase

import cocotb


class test_array_02(cohdl.Entity):
    clk = Port.input(Bit)

    enable_in = Port.input(Bit)
    index_in = Port.input(Unsigned[5])
    data_in = Port.input(BitVector[32])

    index_out = Port.input(Unsigned[5])
    data_out = Port.output(BitVector[32])

    def architecture(self):
        clk = std.Clock(self.clk)

        memory = std.Array[BitVector[32], 32]()

        @std.sequential(clk)
        def proc_in():
            if self.enable_in:
                memory[self.index_in] <<= self.data_in

        @std.sequential(clk)
        def proc_out():
            self.data_out <<= memory[self.index_out]


class Mock(MockBase):
    def __init__(self, dut: test_array_02, *, record=False, no_assert=False):
        super().__init__(dut.clk, record=record, no_assert=no_assert)
        cv = cocotb_util.ConstraindValue

        self.enable_in = self.inpair(dut.enable_in, cv(1), "enable_in")
        self.index_in = self.inpair(dut.index_in, cv(5), "index_in")
        self.data_in = self.inpair(dut.data_in, cv(32), "data_in")

        self.index_out = self.inpair(dut.index_out, cv(5), "index_out")
        self.data_out = self.outpair(dut.data_out, cv(32), "data_out")

        self.memory = [None] * 32

    def mock(self):
        rd_mem = self.memory[self.index_out.get()]
        self.data_out.assign(rd_mem)

        if self.enable_in:
            self.memory[self.index_in.get()] = self.data_in.get()

        if False:
            # turn mock into a generator
            yield


@cocotb.test()
async def testbench_array_02(dut: test_array_02):
    mock = Mock(dut)
    mock.zero_inputs()
    await mock.tick()

    for _ in range(128):
        await mock.next_step()
        mock.enable_in.randomize()
        mock.index_in.randomize()
        mock.index_out.randomize()
        mock.data_in.randomize()


class Unittest(unittest.TestCase):
    def test_array_02(self):
        cohdl_testutil.run_cocotb_tests(test_array_02, __file__, self.__module__)
