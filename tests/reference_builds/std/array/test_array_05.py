from __future__ import annotations

import unittest

import cohdl
from cohdl import std, Bit, BitVector, Port, Unsigned, Signed, Null, Full

import cohdl_testutil

from cohdl_testutil import cocotb_util
from cohdl_testutil.cocotb_mock import MockBase

import cocotb


class test_array_05(cohdl.Entity):
    clk = Port.input(Bit)

    mode = Port.input(int)

    addr_0 = Port.input(Unsigned[3])
    addr_1 = Port.input(Unsigned[3])
    addr_2 = Port.input(Unsigned[3])
    addr_3 = Port.input(Unsigned[3])

    data_0 = Port.input(BitVector[8])
    data_1 = Port.input(BitVector[8])
    data_2 = Port.input(BitVector[8])
    data_3 = Port.input(BitVector[8])

    out_0 = Port.output(BitVector[8], default=Null)
    out_1 = Port.output(BitVector[8], default=Null)
    out_2 = Port.output(BitVector[8], default=Null)
    out_3 = Port.output(BitVector[8], default=Null)
    out_4 = Port.output(BitVector[8], default=Null)
    out_5 = Port.output(BitVector[8], default=Null)
    out_6 = Port.output(BitVector[8], default=Null)
    out_7 = Port.output(BitVector[8], default=Null)

    def architecture(self):
        clk = std.Clock(self.clk)
        memory = std.Array[BitVector[8], 8](Null)

        @std.concurrent
        def logic():
            self.out_0 <<= memory[0]
            self.out_1 <<= memory[1]
            self.out_2 <<= memory[2]
            self.out_3 <<= memory[3]
            self.out_4 <<= memory[4]
            self.out_5 <<= memory[5]
            self.out_6 <<= memory[6]
            self.out_7 <<= memory[7]

        @std.sequential(clk)
        def proc_in():
            nonlocal memory

            match self.mode:
                case 0:
                    memory <<= Null
                case 1:
                    memory <<= Full
                case 2:
                    memory <<= [
                        self.data_0,
                        self.data_1,
                        self.data_2,
                        self.data_3,
                        self.data_0,
                        self.data_1,
                        self.data_2,
                        self.data_3,
                    ]
                case 3:
                    memory <<= {
                        self.addr_0: self.data_0,
                        self.addr_1: self.data_1,
                    }
                case 4:
                    memory <<= {
                        self.addr_0 ^ self.addr_2: self.data_0 & self.data_2,
                        self.addr_1 ^ self.addr_3: self.data_1 | self.data_3,
                    }
                case 5:
                    memory <<= {
                        0: Null,
                        1: Full,
                        2: self.data_0,
                        3: self.data_1,
                        4: self.data_2,
                        5: self.data_3,
                        self.addr_0: self.data_0,
                        self.addr_1: self.data_1,
                        self.addr_2: self.data_2,
                        self.addr_3: self.data_3,
                    }


class Mock(MockBase):
    def __init__(self, dut: test_array_05, *, record=False, no_assert=False):
        super().__init__(dut.clk, record=record, no_assert=no_assert)
        cv = cocotb_util.ConstraindValue

        self.mode = self.inpair(dut.mode, cv(3), "mode")

        self.addr_0 = self.inpair(dut.addr_0, cv(3), "addr_0")
        self.addr_1 = self.inpair(dut.addr_1, cv(3), "addr_1")
        self.addr_2 = self.inpair(dut.addr_2, cv(3), "addr_2")
        self.addr_3 = self.inpair(dut.addr_3, cv(3), "addr_3")

        self.data_0 = self.inpair(dut.data_0, cv(8), "data_0")
        self.data_1 = self.inpair(dut.data_1, cv(8), "data_1")
        self.data_2 = self.inpair(dut.data_2, cv(8), "data_2")
        self.data_3 = self.inpair(dut.data_3, cv(8), "data_3")

        self.out_0 = self.outpair(dut.out_0, cv(8), "out_0")
        self.out_1 = self.outpair(dut.out_1, cv(8), "out_1")
        self.out_2 = self.outpair(dut.out_2, cv(8), "out_2")
        self.out_3 = self.outpair(dut.out_3, cv(8), "out_3")
        self.out_4 = self.outpair(dut.out_4, cv(8), "out_4")
        self.out_5 = self.outpair(dut.out_5, cv(8), "out_5")
        self.out_6 = self.outpair(dut.out_6, cv(8), "out_6")
        self.out_7 = self.outpair(dut.out_7, cv(8), "out_7")

        self.memory = [0] * 8

    def mock(self):

        match self.mode.get():
            case 0:
                self.memory = [0] * 8
            case 1:
                self.memory = [0xFF] * 8
            case 2:
                self.memory = [
                    self.data_0.get(),
                    self.data_1.get(),
                    self.data_2.get(),
                    self.data_3.get(),
                    self.data_0.get(),
                    self.data_1.get(),
                    self.data_2.get(),
                    self.data_3.get(),
                ]
            case 3:
                self.memory[self.addr_0.get()] = self.data_0.get()
                self.memory[self.addr_1.get()] = self.data_1.get()
            case 4:
                self.memory[self.addr_0.get() ^ self.addr_2.get()] = (
                    self.data_0.get() & self.data_2.get()
                )
                self.memory[self.addr_1.get() ^ self.addr_3.get()] = (
                    self.data_1.get() | self.data_3.get()
                )
            case 5:
                self.memory[0] = 0
                self.memory[1] = 0xFF
                self.memory[2] = self.data_0.get()
                self.memory[3] = self.data_1.get()
                self.memory[4] = self.data_2.get()
                self.memory[5] = self.data_3.get()
                self.memory[self.addr_0.get()] = self.data_0.get()
                self.memory[self.addr_1.get()] = self.data_1.get()
                self.memory[self.addr_2.get()] = self.data_2.get()
                self.memory[self.addr_3.get()] = self.data_3.get()

        self.out_0.assign(self.memory[0])
        self.out_1.assign(self.memory[1])
        self.out_2.assign(self.memory[2])
        self.out_3.assign(self.memory[3])
        self.out_4.assign(self.memory[4])
        self.out_5.assign(self.memory[5])
        self.out_6.assign(self.memory[6])
        self.out_7.assign(self.memory[7])

        if False:
            # turn mock into a generator
            yield


@cocotb.test()
async def testbench_array_05(dut: test_array_05):
    mock = Mock(dut)
    mock.zero_inputs()
    await mock.tick()

    for _ in range(128):
        await mock.next_step()
        mock.mode.randomize()

        mock.addr_0.randomize()
        mock.addr_1.randomize()
        mock.addr_2.randomize()
        mock.addr_3.randomize()

        mock.data_0.randomize()
        mock.data_1.randomize()
        mock.data_2.randomize()
        mock.data_3.randomize()


class Unittest(unittest.TestCase):
    def test_array_05(self):
        cohdl_testutil.run_cocotb_tests(test_array_05, __file__, self.__module__)
