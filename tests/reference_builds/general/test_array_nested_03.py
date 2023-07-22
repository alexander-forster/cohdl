from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Signal, Array, enum, Unsigned

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


class test_array_nested_03(cohdl.Entity):
    clk = Port.input(Bit)
    rd_addr_a = Port.input(Unsigned[3])
    rd_addr_b = Port.input(Unsigned[2])
    rd_addr_c = Port.input(Unsigned[2])
    rd_data_enum = Port.output(BitVector[2])
    rd_data_vec = Port.output(BitVector[4])

    wr_addr_a = Port.input(Unsigned[3])
    wr_addr_b = Port.input(Unsigned[2])
    wr_addr_c = Port.input(Unsigned[2])
    wr_data = Port.input(BitVector[4])

    def architecture(self):
        mem_enum = Signal[Array[Array[Array[MyEnum, 4], 4], 8]]()
        mem_vec = Signal[Array[Array[Array[BitVector[4], 4], 4], 8]]()

        @std.sequential(std.Clock(self.clk))
        def proc_enum():
            self.rd_data_enum <<= MyEnum.to_bv(
                mem_enum[self.rd_addr_a][self.rd_addr_b][self.rd_addr_c]
            )
            mem_enum[self.wr_addr_a][self.wr_addr_b][self.wr_addr_c] <<= MyEnum.from_bv(
                self.wr_data[1:0]
            )

        @std.sequential(std.Clock(self.clk))
        def proc_vec():
            rd_data = self.rd_data_vec
            wr_data = self.wr_data

            rd_addr_a, rd_addr_b, rd_addr_c = (
                self.rd_addr_a,
                self.rd_addr_b,
                self.rd_addr_c,
            )

            wr_addr_a, wr_addr_b, wr_addr_c = (
                self.wr_addr_a,
                self.wr_addr_b,
                self.wr_addr_c,
            )

            rd_data[2:0] <<= mem_vec[rd_addr_a][rd_addr_b][rd_addr_c][2:0]
            rd_data[3] <<= mem_vec[rd_addr_a][rd_addr_b][rd_addr_c][3]

            mem_vec[wr_addr_a][wr_addr_b][wr_addr_c][0] <<= wr_data[0]
            mem_vec[wr_addr_a][wr_addr_b][wr_addr_c][3:1] <<= wr_data[3:1]


#
# test code
#


@cocotb_util.test()
async def testbench_functions(dut: test_array_nested_03):
    seq_test = cocotb_util.SequentialTest(dut.clk)

    data_gen = cocotb_util.ConstrainedGenerator(4)
    addr_a_gen = cocotb_util.ConstrainedGenerator(3)
    addr_b_gen = cocotb_util.ConstrainedGenerator(2)
    addr_c_gen = cocotb_util.ConstrainedGenerator(2)

    memory = [[[0] * 4 for _ in range(4)] for _ in range(8)]
    await seq_test.tick()

    for addr_a in addr_a_gen.all():
        for addr_b in addr_b_gen.all():
            for addr_c in addr_c_gen.all():
                value = data_gen.random()
                memory[addr_a.as_int()][addr_b.as_int()][addr_c.as_int()] = value

                cocotb_util.assign(dut.wr_data, value)
                cocotb_util.assign(dut.rd_addr_a, addr_a)
                cocotb_util.assign(dut.rd_addr_b, addr_b)
                cocotb_util.assign(dut.rd_addr_c, addr_c)
                cocotb_util.assign(dut.wr_addr_a, addr_a)
                cocotb_util.assign(dut.wr_addr_b, addr_b)
                cocotb_util.assign(dut.wr_addr_c, addr_c)

                await seq_test.tick()
                await seq_test.tick()

                assert cocotb_util.compare(dut.rd_data_vec, value)
                assert cocotb_util.compare(dut.rd_data_enum, value.get_slice(0, 1))

    for rd_addr_a, rd_addr_b, rd_addr_c, wr_addr_a, wr_addr_b, wr_addr_c, data in zip(
        addr_a_gen.random(128),
        addr_b_gen.random(128),
        addr_c_gen.random(128),
        addr_a_gen.random(128),
        addr_b_gen.random(128),
        addr_c_gen.random(128),
        data_gen.random(128),
    ):
        cocotb_util.assign(dut.wr_addr_a, wr_addr_a)
        cocotb_util.assign(dut.wr_addr_b, wr_addr_b)
        cocotb_util.assign(dut.wr_addr_c, wr_addr_c)
        cocotb_util.assign(dut.rd_addr_a, rd_addr_a)
        cocotb_util.assign(dut.rd_addr_b, rd_addr_b)
        cocotb_util.assign(dut.rd_addr_c, rd_addr_c)
        cocotb_util.assign(dut.wr_data, data)
        memory[wr_addr_a.as_int()][wr_addr_b.as_int()][wr_addr_c.as_int()] = data

        await seq_test.tick()
        await seq_test.tick()

        rd_val = memory[rd_addr_a.as_int()][rd_addr_b.as_int()][rd_addr_c.as_int()]

        assert cocotb_util.compare(dut.rd_data_vec, rd_val)
        assert cocotb_util.compare(dut.rd_data_enum, rd_val.get_slice(0, 1))


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_array_nested_03, __file__, self.__module__)
