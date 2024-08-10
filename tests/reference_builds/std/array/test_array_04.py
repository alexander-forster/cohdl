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


class test_array_04(cohdl.Entity):
    clk = Port.input(Bit)

    enable_in = Port.input(Bit)
    target_in = Port.input(Unsigned[2])
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

        memory = std.Array[TestRecord, 32](Null)

        @std.sequential(clk)
        def proc_in():
            if self.enable_in:
                match self.target_in:
                    case 0:
                        memory[self.index_in] <<= std.from_bits[TestRecord](
                            self.data_in
                        )
                    case 1:
                        memory[self.index_in].a <<= std.from_bits[TestRecord](
                            self.data_in
                        ).a
                    case 2:
                        memory[self.index_in].b <<= std.from_bits[TestRecord](
                            self.data_in
                        ).b
                        memory[self.index_in].sub.x <<= std.from_bits[TestRecord](
                            self.data_in
                        ).sub.y
                    case 3:
                        memory[self.index_in].a <<= Null
                        memory[self.index_in].d <<= std.from_bits[TestRecord](
                            self.data_in
                        ).d

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
    def __init__(self, dut: test_array_04, *, record=False, no_assert=False):
        super().__init__(dut.clk, record=record, no_assert=no_assert)
        cv = cocotb_util.ConstraindValue

        self.enable_in = self.inpair(dut.enable_in, cv(1), "enable_in")
        self.index_in = self.inpair(dut.index_in, cv(5), "index_in")
        self.target_in = self.inpair(dut.target_in, cv(2), "target_in")
        self.data_in = self.inpair(dut.data_in, cv(32), "data_in")

        self.index_out = self.inpair(dut.index_out, cv(5), "index_out")
        self.data_out = self.outpair(dut.data_out, cv(32), "data_out")
        self.a_out = self.outpair(dut.a_out, cv(1), "a_out")
        self.b_out = self.outpair(dut.b_out, cv(7), "b_out")
        self.c_out = self.outpair(dut.c_out, cv(8), "c_out")
        self.d_out = self.outpair(dut.d_out, cv(8), "d_out")
        self.x_out = self.outpair(dut.x_out, cv(4), "x_out")
        self.y_out = self.outpair(dut.y_out, cv(4), "y_out")

        self.memory = [0] * 32

    def mock(self):
        rd_mem: cocotb_util.ConstraindValue = self.memory[self.index_out.get()]
        self.data_out.assign(rd_mem)
        rd_mem = cocotb_util.ConstraindValue(32, rd_mem)

        self.a_out.assign(rd_mem.get_slice(0, 0))
        self.b_out.assign(rd_mem.get_slice(1, 7))
        self.c_out.assign(rd_mem.get_slice(8, 15))
        self.d_out.assign(rd_mem.get_slice(16, 23))
        self.x_out.assign(rd_mem.get_slice(24, 27))
        self.y_out.assign(rd_mem.get_slice(28, 31))

        if self.enable_in:
            index = self.index_in.get()
            prev = self.memory[index]
            data = self.data_in.get()

            match self.target_in.get():
                case 0:
                    self.memory[index] = data
                case 1:
                    self.memory[index] = (prev & ~1) | (data & 1)
                case 2:
                    self.memory[index] = (
                        (prev & ~0x0F0000FE)
                        | (data & 0xFE)
                        | ((data >> 4) & 0x0F00_0000)
                    )
                case 3:
                    self.memory[index] = (prev & ~0x00FF0001) | (data & 0x00FF0000)
                case _:
                    raise AssertionError("invalid target value")

        if False:
            # turn mock into a generator
            yield


@cocotb.test()
async def testbench_array_04(dut: test_array_04):
    mock = Mock(dut)
    mock.zero_inputs()
    mock.enable_in.assign(1)
    mock.target_in.assign(1)
    await mock.tick()

    for _ in range(16):
        await mock.next_step()
        mock.enable_in.randomize()
        mock.target_in.randomize()
        mock.index_in.randomize()
        mock.data_in.randomize()
        mock.index_out.randomize()


class Unittest(unittest.TestCase):
    def test_array_04(self):
        cohdl_testutil.run_cocotb_tests(test_array_04, __file__, self.__module__)
