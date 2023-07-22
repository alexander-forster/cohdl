from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Signal, Array, enum

from cohdl import std

from cohdl_testutil import cocotb_util


class MyEnum(enum.Enum):
    a = enum.auto()
    b = enum.auto()
    c = enum.auto()
    d = enum.auto()

    @staticmethod
    def from_bv(bv):
        return std.select[MyEnum](
            bv,
            {
                "00": MyEnum.a,
                "01": MyEnum.b,
                "10": MyEnum.c,
                "11": MyEnum.d,
            },
        )

    @staticmethod
    def to_bv(e):
        return std.select[BitVector[2]](
            e,
            {
                MyEnum.a: BitVector[2]("00"),
                MyEnum.b: BitVector[2]("01"),
                MyEnum.c: BitVector[2]("10"),
                MyEnum.d: BitVector[2]("11"),
            },
        )


class test_array_nested_02(cohdl.Entity):
    clk = Port.input(Bit)
    rd_addr_a = Port.input(BitVector[3])
    rd_addr_b = Port.input(BitVector[2])
    rd_data = Port.output(BitVector[2])

    wr_addr_a = Port.input(BitVector[3])
    wr_addr_b = Port.input(BitVector[2])
    wr_data = Port.input(BitVector[2])

    def architecture(self):
        mem = Signal[Array[Array[MyEnum, 4], 8]]()

        @std.sequential(std.Clock(self.clk))
        def proc():
            self.rd_data <<= MyEnum.to_bv(
                mem[self.rd_addr_a.unsigned][self.rd_addr_b.unsigned]
            )
            mem[self.wr_addr_a.unsigned][self.wr_addr_b.unsigned] <<= MyEnum.from_bv(
                self.wr_data
            )


#
# test code
#


@cocotb_util.test()
async def testbench_functions(dut: test_array_nested_02):
    seq_test = cocotb_util.SequentialTest(dut.clk)

    data_gen = cocotb_util.ConstrainedGenerator(2)
    addr_a_gen = cocotb_util.ConstrainedGenerator(3)
    addr_b_gen = cocotb_util.ConstrainedGenerator(2)

    memory = [[0] * 8 for _ in range(16)]
    await seq_test.tick()

    for addr_a in addr_a_gen.all():
        for addr_b in addr_b_gen.all():
            value = data_gen.random()
            memory[addr_a.as_int()][addr_b.as_int()] = value

            cocotb_util.assign(dut.wr_data, value)
            cocotb_util.assign(dut.rd_addr_a, addr_a)
            cocotb_util.assign(dut.rd_addr_b, addr_b)
            cocotb_util.assign(dut.wr_addr_a, addr_a)
            cocotb_util.assign(dut.wr_addr_b, addr_b)

            await seq_test.tick()
            await seq_test.tick()

            assert cocotb_util.compare(dut.rd_data, value)

    for rd_addr_a, rd_addr_b, wr_addr_a, wr_addr_b, data in zip(
        addr_a_gen.random(128),
        addr_b_gen.random(128),
        addr_a_gen.random(128),
        addr_b_gen.random(128),
        data_gen.random(128),
    ):
        cocotb_util.assign(dut.wr_addr_a, wr_addr_a)
        cocotb_util.assign(dut.wr_addr_b, wr_addr_b)
        cocotb_util.assign(dut.rd_addr_a, rd_addr_a)
        cocotb_util.assign(dut.rd_addr_b, rd_addr_b)
        cocotb_util.assign(dut.wr_data, data)
        memory[wr_addr_a.as_int()][wr_addr_b.as_int()] = data

        await seq_test.tick()
        await seq_test.tick()

        assert cocotb_util.compare(
            dut.rd_data, memory[rd_addr_a.as_int()][rd_addr_b.as_int()]
        )


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(
            test_array_nested_02,
            __file__,
            self.__module__,
        )
