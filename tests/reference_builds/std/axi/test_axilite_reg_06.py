from __future__ import annotations

from cocotbext.axi import AxiLiteBus, AxiLiteMaster

import cohdl
from cohdl import Port, Bit, BitVector, Unsigned, Signed, Null, Full
from cohdl import std

from cohdl.std.axi import axi4_light as axi

from cohdl.std.reg import reg32


class MyRoot(reg32.AddrMap, word_count=8):
    reg_word: reg32.Word[0x00]
    reg_uword: reg32.UWord[0x04]
    reg_sword: reg32.SWord[0x08]

    reg_mem_word: reg32.MemWord[0x10]
    reg_mem_uword: reg32.MemUWord[0x14]
    reg_mem_sword: reg32.MemSWord[0x18]

    def _config_(self):
        self.reg_mem_uword._config_(1234)
        self.reg_mem_sword._config_(5555)

    def _impl_concurrent_(self) -> None:
        self.reg_word <<= self.reg_mem_word
        self.reg_uword <<= self.reg_mem_uword.val()
        self.reg_sword.raw <<= self.reg_mem_sword.raw


class test_axilite_reg_06(cohdl.Entity):
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

        axi_con.connect_addr_map(MyRoot())


import unittest
import cohdl_testutil
import cocotb


@cocotb.test()
async def testbench_axilite_reg_06(dut: test_axilite_reg_06):
    rnd_data = cohdl_testutil.cocotb_util.ConstrainedGenerator(32)
    rnd_index = cohdl_testutil.cocotb_util.ConstrainedGenerator(2)

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

    val_a = 0
    val_b = 1234
    val_c = 5555

    async def check_content():
        assert (await axi_master.read_dword(0x00)) == val_a
        assert (await axi_master.read_dword(0x04)) == val_b
        assert (await axi_master.read_dword(0x08)) == val_c
        assert (await axi_master.read_dword(0x10)) == val_a
        assert (await axi_master.read_dword(0x14)) == val_b
        assert (await axi_master.read_dword(0x18)) == val_c

    await check_content()
    await axi_master.write_dword(0x00, 0xFFFFFFFF)
    await check_content()
    await axi_master.write_dword(0x04, 0xFFFFFFFF)
    await check_content()
    await axi_master.write_dword(0x08, 0xFFFFFFFF)
    await check_content()

    await axi_master.write_dword(0x10, val_a := 1)
    await check_content()
    await axi_master.write_dword(0x14, val_b := 2)
    await check_content()
    await axi_master.write_dword(0x18, val_c := 3)
    await check_content()

    await axi_master.write_byte(0x11, 0x55)
    val_a = 0x5501
    await check_content()

    await axi_master.write_byte(0x16, 0x77)
    val_b = 0x770002
    await check_content()

    await axi_master.write_byte(0x1B, 0x99)
    val_c = 0x99000003
    await check_content()


class Unittest(unittest.TestCase):
    def test_axilite_reg_06(self):
        cohdl_testutil.run_cocotb_tests(test_axilite_reg_06, __file__, self.__module__)
