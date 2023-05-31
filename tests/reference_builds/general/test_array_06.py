from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Signal, Array, Unsigned, Signed

from cohdl import std

from cohdl_testutil import cocotb_util


class test_array_06(cohdl.Entity):
    clk = Port.input(Bit)
    reset = Port.input(Bit)

    addr = Port.input(Unsigned[2])

    rd_v_v = Port.output(BitVector[4])
    rd_v_s = Port.output(Signed[4])
    rd_v_u = Port.output(Unsigned[4])
    rd_v_long_s = Port.output(Signed[8])
    rd_v_long_u = Port.output(Unsigned[8])

    rd_s_v = Port.output(BitVector[4])
    rd_s_s = Port.output(Signed[4])
    rd_s_u = Port.output(Unsigned[4])
    rd_s_long_s = Port.output(Signed[8])
    rd_s_long_u = Port.output(Unsigned[8])

    rd_u_v = Port.output(BitVector[4])
    rd_u_s = Port.output(Signed[4])
    rd_u_u = Port.output(Unsigned[4])
    rd_u_long_s = Port.output(Signed[8])
    rd_u_long_u = Port.output(Unsigned[8])

    def architecture(self):
        default = ["0000", "1001", "0111", "1111"]

        array_vector = Signal[Array[BitVector[4], 4]](default)
        array_signed = Signal[Array[Signed[4], 4]](default)
        array_unsigned = Signal[Array[Unsigned[4], 4]](default)

        @std.concurrent
        def logic():
            self.rd_v_v <<= array_vector[self.addr]
            self.rd_v_s <<= array_vector[self.addr].signed
            self.rd_v_u <<= array_vector[self.addr].unsigned
            self.rd_v_long_s <<= array_vector[self.addr].signed
            self.rd_v_long_u <<= array_vector[self.addr].unsigned

            self.rd_s_v <<= array_signed[self.addr]
            self.rd_s_s <<= array_signed[self.addr].signed
            self.rd_s_u <<= array_signed[self.addr].unsigned
            self.rd_s_long_s <<= array_signed[self.addr].signed
            self.rd_s_long_u <<= array_signed[self.addr].unsigned

            self.rd_u_v <<= array_unsigned[self.addr]
            self.rd_u_s <<= array_unsigned[self.addr].signed
            self.rd_u_u <<= array_unsigned[self.addr].unsigned
            self.rd_u_long_s <<= array_unsigned[self.addr].signed
            self.rd_u_long_u <<= array_unsigned[self.addr].unsigned


#
# test code
#


@cocotb_util.test()
async def testbench_functions(dut: test_array_06):
    seq = cocotb_util.SequentialTest(dut.clk)

    bit_gen = cocotb_util.ConstrainedGenerator(1)

    default_short = ["0000", "1001", "0111", "1111"]
    default_long_u = ["00000000", "00001001", "00000111", "00001111"]
    default_long_s = ["00000000", "11111001", "00000111", "11111111"]

    for addr in [0, 1, 2, 3]:
        reset = bit_gen.random()

        short = default_short[addr]
        long_u = default_long_u[addr]
        long_s = default_long_s[addr]

        await seq.check_next_tick(
            [
                (dut.reset, reset),
                (dut.addr, addr),
            ],
            [
                (dut.rd_v_v, short),
                (dut.rd_v_s, short),
                (dut.rd_v_u, short),
                (dut.rd_v_long_s, long_s),
                (dut.rd_v_long_u, long_u),
                (dut.rd_s_v, short),
                (dut.rd_s_s, short),
                (dut.rd_s_u, short),
                (dut.rd_s_long_s, long_s),
                (dut.rd_s_long_u, long_u),
                (dut.rd_u_v, short),
                (dut.rd_u_s, short),
                (dut.rd_u_u, short),
                (dut.rd_u_long_s, long_s),
                (dut.rd_u_long_u, long_u),
            ],
        )


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_array_06, __file__, self.__module__)
