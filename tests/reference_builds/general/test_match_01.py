from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Null

from cohdl import std

import cohdl_testutil

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge


ConstrainedGenerator = cohdl_testutil.cocotb_util.ConstrainedGenerator


class test_match_01(cohdl.Entity):
    clk = Port.input(Bit)

    sw = Port.input(BitVector[4])

    out_a = Port.output(Bit)
    out_b = Port.output(BitVector[1])
    out_c = Port.output(BitVector[2])
    out_d = Port.output(BitVector[4])

    def architecture(self):
        clk = std.Clock(self.clk)

        @std.sequential(clk)
        def proc_simple():
            match self.sw:
                case "0000":
                    self.out_a <<= False
                    self.out_b <<= Null
                    self.out_c <<= Null
                    self.out_d <<= Null
                case "0001":
                    self.out_a <<= True
                    self.out_d <<= "1011"
                case "1010":
                    self.out_c <<= "11"
                case "1110":
                    self.out_d <<= self.sw if self.out_a else ~self.sw
                case cohdl.Full:
                    self.out_a <<= True
                case _:
                    self.out_a <<= False


@cocotb.test()
async def testbench_match_simple(dut: test_match_01):
    cocotb.start_soon(Clock(dut.clk, 1, units="ns").start())

    # set initial value of outputs
    await cohdl_testutil.cocotb_util.check_sequential(
        RisingEdge(dut.clk),
        [(dut.sw, "0000")],
        [],
    )

    out_a = 0
    out_b = 0
    out_c = 0
    out_d = 0

    for sw in ConstrainedGenerator(4).all():
        sw_str = sw.as_str()

        match sw_str:
            case "0000":
                out_a = 0
                out_b = 0
                out_c = 0
                out_d = 0
            case "0001":
                out_a = 1
                out_d = "1011"
            case "1010":
                out_c = 3
            case "1110":
                out_d = sw if out_a else sw.inverse()
            case "1111":
                out_a = 1
            case _:
                out_a = 0

        await cohdl_testutil.cocotb_util.check_sequential(
            RisingEdge(dut.clk),
            [(dut.sw, sw)],
            [
                (dut.out_a, out_a),
                (dut.out_b, out_b),
                (dut.out_c, out_c),
                (dut.out_d, out_d),
            ],
            check_msg=f"{sw=}",
        )


class Unittest(unittest.TestCase):
    def test_match_simple(self):
        cohdl_testutil.run_cocotb_tests(test_match_01, __file__, self.__module__)
