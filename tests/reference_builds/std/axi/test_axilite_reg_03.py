from __future__ import annotations

from cocotbext.axi import AxiLiteBus, AxiLiteMaster

import cohdl
from cohdl import Port, Bit, BitVector, Signal, Unsigned, Null
from cohdl import std

from cohdl.std.axi import axi4_light as axi

from cohdl.std.reg import reg32


class MyRegister(reg32.Register):
    cnt: reg32.UField[15:0, Null]

    flag: reg32.FlagField[31]

    async def _impl_sequential_(self) -> None:
        counter = Signal[Unsigned[8]](0)

        async with self.flag.flag():
            while counter < 16:
                counter <<= counter + 1
            self.cnt <<= self.cnt.value() + 1


class MyRoot(reg32.AddrMap, word_count=4):
    reg_array: reg32.Array[MyRegister, 0:16:4]


class test_axilite_reg_03(cohdl.Entity):
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

        axi_con.connect_root_device(MyRoot())


import unittest
import cohdl_testutil
import cocotb


@cocotb.test()
async def testbench_axilite_reg_03(dut: test_axilite_reg_03):
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

    await axi_master.write_dword(0, 0xF0000000)
    assert (await axi_master.read_dword(0)) == 0x80000000
    await seq.tick(16)
    assert (await axi_master.read_dword(0)) == 0x00000001

    await axi_master.write_dword(12, 0xF0000000)
    await axi_master.write_dword(12, 0xF0000000)
    await axi_master.write_dword(8, 0xF0000000)
    await axi_master.write_dword(4, 0xF0000000)
    await axi_master.write_dword(0, 0xF0000000)

    assert (await axi_master.read_dword(12)) == 0x80000000
    assert (await axi_master.read_dword(8)) == 0x80000000
    assert (await axi_master.read_dword(4)) == 0x80000000
    assert (await axi_master.read_dword(0)) == 0x80000001

    await seq.tick(16)
    assert (await axi_master.read_dword(12)) == 0x00000001
    assert (await axi_master.read_dword(8)) == 0x00000001
    assert (await axi_master.read_dword(4)) == 0x00000001
    assert (await axi_master.read_dword(0)) == 0x00000002


class Unittest(unittest.TestCase):
    def test_axilite_reg_03(self):
        cohdl_testutil.run_cocotb_tests(test_axilite_reg_03, __file__, self.__module__)
