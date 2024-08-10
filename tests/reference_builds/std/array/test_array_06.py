from __future__ import annotations

import unittest

import cohdl
from cohdl import std, Bit, BitVector, Port, Unsigned, Signed, Null, Full

import cohdl_testutil

from cohdl_testutil import cocotb_util
from cohdl_testutil.cocotb_mock import MockBase

import cocotb


class test_array_06(cohdl.Entity):
    clk = Port.input(Bit)

    mode = Port.input(int)

    addr_0 = Port.input(Unsigned[3])
    addr_1 = Port.input(Unsigned[3])
    addr_2 = Port.input(Unsigned[3])
    addr_3 = Port.input(Unsigned[3])

    data_0 = Port.input(BitVector[4])
    data_1 = Port.input(BitVector[4])
    data_2 = Port.input(BitVector[4])
    data_3 = Port.input(BitVector[4])
    data_4 = Port.input(BitVector[4])
    data_5 = Port.input(BitVector[4])
    data_6 = Port.input(BitVector[4])
    data_7 = Port.input(BitVector[4])

    out_0 = Port.output(BitVector[4], default=Null)
    out_1 = Port.output(BitVector[4], default=Null)
    out_2 = Port.output(BitVector[4], default=Null)
    out_3 = Port.output(BitVector[4], default=Null)
    out_4 = Port.output(BitVector[4], default=Null)
    out_5 = Port.output(BitVector[4], default=Null)
    out_6 = Port.output(BitVector[4], default=Null)
    out_7 = Port.output(BitVector[4], default=Null)

    def architecture(self):
        with std.prefix("arr_inp"):
            arr_in = std.Array[BitVector[4], 8](Null)

        arr_out = std.Array[BitVector[4], 8](
            Null, _qualifier_=std.NamedQualifier[std.Signal, "arr_out"]
        )

        @std.concurrent
        def logic():
            nonlocal arr_in
            arr_in <<= [
                self.data_0,
                self.data_1,
                self.data_2,
                self.data_3,
                self.data_4,
                self.data_5,
                self.data_6,
                self.data_7,
            ]

            self.out_0 <<= arr_out[0]
            self.out_1 <<= arr_out[1]
            self.out_2 <<= arr_out[2]
            self.out_3 <<= arr_out[3]
            self.out_4 <<= arr_out[4]
            self.out_5 <<= arr_out[5]
            self.out_6 <<= arr_out[6]
            self.out_7 <<= arr_out[7]

        @std.sequential(std.Clock(self.clk))
        def proc_in():
            nonlocal arr_out

            match self.mode:
                case 0:
                    arr_out[0, 1] <<= Null
                    arr_out[2:4] <<= Full
                    arr_out[7:5] <<= Null
                case 1:
                    arr_out[::2] <<= Full
                    arr_out[1::2] <<= Null
                case 2:
                    arr_out <<= arr_in[0, 1, 2, 2, 4, 0, 6, 7]
                case 3:

                    # arr_out[0] <<= arr_in[0]

                    if True:
                        arr_out[::-1] <<= [
                            arr_in[0],
                            arr_in[1],
                            arr_in[2],
                            arr_in[3],
                            arr_in[4],
                            arr_in[5],
                            arr_in[6],
                            arr_in[7],
                        ]
                case 4:
                    arr_out[0, 2, 4, 6] <<= {
                        0: arr_in[3],
                        1: arr_in[0],
                        3: arr_in[1],
                        2: arr_in[1],
                    }

                    arr_out[1, 3, 5, 7] <<= arr_in[3:2, 4:5]
                case 5:
                    arr_out[self.addr_0, self.addr_1] <<= arr_in[self.addr_3, 5]
                case 6:
                    arr_out[self.addr_0, self.addr_3, self.addr_2][1] <<= arr_in[
                        self.addr_2
                    ]
                case 7:
                    arr_out[0, self.addr_3].set_elem(1, arr_in[3])
                    arr_out[0, self.addr_3].set_elem(0, arr_in.get_elem(self.addr_2))

                    arr_out.set_elem(self.addr_1, arr_in.get_elem(1, std.Value))

                    arr_out[7:0][2] <<= arr_in.get_elem(2, std.Temporary)


class Mock(MockBase):
    def __init__(self, dut: test_array_06, *, record=False, no_assert=False):
        super().__init__(dut.clk, record=record, no_assert=no_assert)
        cv = cocotb_util.ConstraindValue

        self.mode = self.inpair(dut.mode, cv(3), "mode")

        self.addr_0 = self.inpair(dut.addr_0, cv(3), "addr_0")
        self.addr_1 = self.inpair(dut.addr_1, cv(3), "addr_1")
        self.addr_2 = self.inpair(dut.addr_2, cv(3), "addr_2")
        self.addr_3 = self.inpair(dut.addr_3, cv(3), "addr_3")

        self.data_0 = self.inpair(dut.data_0, cv(4), "data_0")
        self.data_1 = self.inpair(dut.data_1, cv(4), "data_1")
        self.data_2 = self.inpair(dut.data_2, cv(4), "data_2")
        self.data_3 = self.inpair(dut.data_3, cv(4), "data_3")
        self.data_4 = self.inpair(dut.data_4, cv(4), "data_4")
        self.data_5 = self.inpair(dut.data_5, cv(4), "data_5")
        self.data_6 = self.inpair(dut.data_6, cv(4), "data_6")
        self.data_7 = self.inpair(dut.data_7, cv(4), "data_7")

        self.out_0 = self.outpair(dut.out_0, cv(4), "out_0")
        self.out_1 = self.outpair(dut.out_1, cv(4), "out_1")
        self.out_2 = self.outpair(dut.out_2, cv(4), "out_2")
        self.out_3 = self.outpair(dut.out_3, cv(4), "out_3")
        self.out_4 = self.outpair(dut.out_4, cv(4), "out_4")
        self.out_5 = self.outpair(dut.out_5, cv(4), "out_5")
        self.out_6 = self.outpair(dut.out_6, cv(4), "out_6")
        self.out_7 = self.outpair(dut.out_7, cv(4), "out_7")

        self.din = [
            self.data_0,
            self.data_1,
            self.data_2,
            self.data_3,
            self.data_4,
            self.data_5,
            self.data_6,
            self.data_7,
        ]

        self.memory = [0, 0, 0xF, 0xF, 0xF, 0, 0, 0]

    def mock(self):
        din = self.din

        match self.mode.get():
            case 0:
                self.memory = [0, 0, 0xF, 0xF, 0xF, 0, 0, 0]
            case 1:
                self.memory = [0xF, 0, 0xF, 0, 0xF, 0, 0xF, 0]
            case 2:
                self.memory = [
                    self.data_0.get(),
                    self.data_1.get(),
                    self.data_2.get(),
                    self.data_2.get(),
                    self.data_4.get(),
                    self.data_0.get(),
                    self.data_6.get(),
                    self.data_7.get(),
                ]
            case 3:
                self.memory = [
                    self.data_7.get(),
                    self.data_6.get(),
                    self.data_5.get(),
                    self.data_4.get(),
                    self.data_3.get(),
                    self.data_2.get(),
                    self.data_1.get(),
                    self.data_0.get(),
                ]
            case 4:
                self.memory[0] = self.data_3.get()
                self.memory[2] = self.data_0.get()
                self.memory[6] = self.data_1.get()
                self.memory[4] = self.data_1.get()

                self.memory[1] = self.data_3.get()
                self.memory[3] = self.data_2.get()
                self.memory[5] = self.data_4.get()
                self.memory[7] = self.data_5.get()
            case 5:
                self.memory[self.addr_0.get()] = din[self.addr_3.get()].get()
                self.memory[self.addr_1.get()] = din[5].get()
            case 6:
                self.memory[self.addr_3.get()] = din[self.addr_2.get()].get()
            case 7:
                self.memory[self.addr_3.get()] = din[3].get()
                self.memory[0] = din[self.addr_2.get()].get()
                self.memory[self.addr_1.get()] = din[1].get()
                self.memory[5] = din[2].get()

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
async def testbench_array_06(dut: test_array_06):
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
        mock.data_4.randomize()
        mock.data_5.randomize()
        mock.data_6.randomize()
        mock.data_7.randomize()


class Unittest(unittest.TestCase):
    def test_array_06(self):
        cohdl_testutil.run_cocotb_tests(test_array_06, __file__, self.__module__)
