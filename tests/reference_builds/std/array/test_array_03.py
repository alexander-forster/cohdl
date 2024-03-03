from __future__ import annotations

import unittest

import cohdl
from cohdl import std, Bit, BitVector, Port, Unsigned, Signed, Null

import cohdl_testutil

from cohdl_testutil import cocotb_util
from cohdl_testutil.cocotb_mock import MockBase

import cocotb


class SubRecord(std.Record):
    x: BitVector[4]
    y: BitVector[4]


class TestRecord(std.Record):
    a: Bit
    b: BitVector[7]
    c: Unsigned[8]
    d: Signed[8]
    sub: SubRecord


class test_array_03(cohdl.Entity):
    clk = Port.input(Bit)

    enable_in = Port.input(Bit)
    index_in = Port.input(Unsigned[5])
    data_in = Port.input(BitVector[32])

    index_out = Port.input(Unsigned[5])
    data_out = Port.output(BitVector[32])

    a_out = Port.output(Bit)
    b_out = Port.output(BitVector[7])
    c_out = Port.output(Unsigned[8])
    d_out = Port.output(Signed[8])
    x_out = Port.output(BitVector[4])
    y_out = Port.output(BitVector[4])

    def architecture(self):
        clk = std.Clock(self.clk)

        memory = std.Array[TestRecord, 32]()

        @std.sequential(clk)
        def proc_in():
            if self.enable_in:
                memory[self.index_in] <<= std.from_bits[TestRecord](self.data_in)

        @std.sequential(clk)
        def proc_out():
            elem = memory[self.index_out]

            self.data_out <<= std.to_bits(elem)
            self.a_out <<= elem.a
            self.b_out <<= elem.b
            self.c_out <<= elem.c
            self.d_out <<= elem.d
            self.x_out <<= elem.sub.x
            self.y_out <<= elem.sub.y


class Mock(MockBase):
    def __init__(self, dut: test_array_03, *, record=False, no_assert=False):
        super().__init__(dut.clk, record=record, no_assert=no_assert)
        cv = cocotb_util.ConstraindValue

        self.enable_in = self.inpair(dut.enable_in, cv(1), "enable_in")
        self.index_in = self.inpair(dut.index_in, cv(5), "index_in")
        self.data_in = self.inpair(dut.data_in, cv(32), "data_in")

        self.index_out = self.inpair(dut.index_out, cv(5), "index_out")
        self.data_out = self.outpair(dut.data_out, cv(32), "data_out")
        self.a_out = self.outpair(dut.a_out, cv(1), "a_out")
        self.b_out = self.outpair(dut.b_out, cv(7), "b_out")
        self.c_out = self.outpair(dut.c_out, cv(8), "c_out")
        self.d_out = self.outpair(dut.d_out, cv(8), "d_out")
        self.x_out = self.outpair(dut.x_out, cv(4), "x_out")
        self.y_out = self.outpair(dut.y_out, cv(4), "y_out")

        self.memory = [None] * 32

    def mock(self):
        rd_mem: cocotb_util.ConstraindValue = self.memory[self.index_out.get()]
        self.data_out.assign(rd_mem)

        if rd_mem is not None:
            rd_mem = cocotb_util.ConstraindValue(32, rd_mem)

            self.a_out.assign(rd_mem.get_slice(0, 0))
            self.b_out.assign(rd_mem.get_slice(1, 7))
            self.c_out.assign(rd_mem.get_slice(8, 15))
            self.d_out.assign(rd_mem.get_slice(16, 23))
            self.x_out.assign(rd_mem.get_slice(24, 27))
            self.y_out.assign(rd_mem.get_slice(28, 31))
        else:
            self.a_out.assign(None)
            self.b_out.assign(None)
            self.c_out.assign(None)
            self.d_out.assign(None)
            self.x_out.assign(None)
            self.y_out.assign(None)

        if self.enable_in:
            self.memory[self.index_in.get()] = self.data_in.get()

        if False:
            # turn mock into a generator
            yield


@cocotb.test()
async def testbench_array_03(dut: test_array_03):
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
    def test_array_03(self):
        cohdl_testutil.run_cocotb_tests(test_array_03, __file__, self.__module__)
