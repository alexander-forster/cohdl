from __future__ import annotations
from typing import Any

from cocotbext.axi import AxiLiteBus, AxiLiteMaster

import cohdl
from cohdl import Port, Bit, BitVector, Unsigned, Null
from cohdl import std

from cohdl.std.axi import axi4_light as axi

from cohdl.std.reg import reg32


class MyRange(reg32.AddrRange, word_count=16):
    def _config_(self, wr_addr, wr_data):
        self._wr_addr = wr_addr
        self._wr_data = wr_data

    def _on_read_(self, addr: Unsigned) -> BitVector:
        return std.leftpad(addr, 32)

    def _on_write_(self, addr: Unsigned, data: BitVector, mask: std.Mask):
        self._wr_addr <<= std.leftpad(addr, 32)
        self._wr_data <<= data


class MyRelativeRange(reg32.AddrRange, word_count=16):
    def _config_(self, wr_addr, wr_data):
        self._wr_addr = wr_addr
        self._wr_data = wr_data

    def _on_read_relative_(self, addr: Unsigned) -> BitVector:
        return std.leftpad(addr, 32)

    def _on_write_relative_(self, addr: Unsigned, data: BitVector, mask: std.Mask):
        self._wr_addr <<= std.leftpad(addr, 32)
        self._wr_data <<= data


class MyRoot(reg32.RootDevice, word_count=128):
    range_low: MyRange[0]
    range_high: MyRelativeRange[64]

    def _config_(self, wr_addr_low, wr_data_low, wr_addr_high, wr_data_high):
        self.range_low._config_(wr_addr_low, wr_data_low)
        self.range_high._config_(wr_addr_high, wr_data_high)


class test_axilite_reg_04(cohdl.Entity):
    clk = Port.input(Bit)
    reset = Port.input(Bit)

    axi_awaddr = Port.input(Unsigned[32])
    axi_awprot = Port.input(Unsigned[3])
    axi_awvalid = Port.input(Bit)
    axi_awready = Port.output(Bit, default=Null)

    axi_wdata = Port.input(BitVector[32])
    axi_wstrb = Port.input(BitVector[4])
    axi_wvalid = Port.input(Bit)
    axi_wready = Port.output(Bit, default=Null)

    axi_bresp = Port.output(BitVector[2], default=Null)
    axi_bvalid = Port.output(Bit, default=Null)
    axi_bready = Port.input(Bit)

    axi_araddr = Port.input(Unsigned[32])
    axi_arprot = Port.input(Unsigned[3])
    axi_arvalid = Port.input(Bit)
    axi_arready = Port.output(Bit, default=Null)

    axi_rdata = Port.output(BitVector[32], default=Null)
    axi_rresp = Port.output(BitVector[2], default=Null)
    axi_rvalid = Port.output(Bit, default=Null)
    axi_rready = Port.input(Bit)

    wr_addr_low = Port.output(BitVector[32])
    wr_data_low = Port.output(BitVector[32])
    wr_addr_high = Port.output(BitVector[32])
    wr_data_high = Port.output(BitVector[32])

    def architecture(self):
        clk = std.Clock(self.clk)
        reset = std.Reset(self.reset)

        axi_con = axi.Axi4Light(
            clk=clk,
            reset=reset,
            wraddr=axi.Axi4Light.WrAddr(
                valid=self.axi_awvalid,
                ready=self.axi_awready,
                awaddr=self.axi_awaddr,
                awprot=self.axi_awprot,
            ),
            wrdata=axi.Axi4Light.WrData(
                valid=self.axi_wvalid,
                ready=self.axi_wready,
                wdata=self.axi_wdata,
                wstrb=self.axi_wstrb,
            ),
            wrresp=axi.Axi4Light.WrResp(
                valid=self.axi_bvalid,
                ready=self.axi_bready,
                bresp=self.axi_bresp,
            ),
            rdaddr=axi.Axi4Light.RdAddr(
                valid=self.axi_arvalid,
                ready=self.axi_arready,
                araddr=self.axi_araddr,
                arprot=self.axi_arprot,
            ),
            rddata=axi.Axi4Light.RdData(
                valid=self.axi_rvalid,
                ready=self.axi_rready,
                rdata=self.axi_rdata,
                rresp=self.axi_rresp,
            ),
        )

        axi_con.connect_root_device(
            MyRoot(
                wr_addr_low=self.wr_addr_low,
                wr_data_low=self.wr_data_low,
                wr_addr_high=self.wr_addr_high,
                wr_data_high=self.wr_data_high,
            )
        )


import unittest
import cohdl_testutil
import cocotb
import random


@cocotb.test()
async def testbench_axilite_reg_04(dut: test_axilite_reg_04):
    seq = cohdl_testutil.cocotb_util.SequentialTest(dut.clk)
    dut.reset.value = 0

    dut.axi_araddr.value = 0
    dut.axi_arprot.value = 0
    dut.axi_arvalid.value = 0
    dut.axi_bready.value = 0
    dut.axi_rready.value = 0
    dut.axi_wstrb.value = 0
    dut.axi_wdata.value = 0
    dut.axi_awvalid.value = 0
    dut.axi_awprot.value = 0
    dut.axi_awaddr.value = 0
    dut.axi_wvalid.value = 0

    bus = AxiLiteBus.from_prefix(dut, "axi")
    axi_master = AxiLiteMaster(bus, dut.clk, dut.reset)

    for addr in range(0, 128, 4):
        result = await axi_master.read_dword(addr)

        if addr < 64:
            assert addr == result
        else:
            assert addr == result + 64

        rnd = random.randint(0, 2**32 - 1)
        await axi_master.write_dword(addr, rnd)

        if addr < 64:
            assert dut.wr_addr_low == addr
            assert dut.wr_data_low == rnd
        else:
            assert dut.wr_addr_high == addr - 64
            assert dut.wr_data_high == rnd


class Unittest(unittest.TestCase):
    def test_axilite_reg_04(self):
        cohdl_testutil.run_cocotb_tests(test_axilite_reg_04, __file__, self.__module__)
