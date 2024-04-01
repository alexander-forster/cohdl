from __future__ import annotations

from cocotbext.axi import AxiLiteBus, AxiLiteMaster

import cohdl
from cohdl import Port, Signal, Bit, BitVector, Unsigned, Signed, Null, Full
from cohdl import std

from cohdl.std.axi import axi4_light as axi

from cohdl.std.reg import reg32


class MyRoot(reg32.AddrMap, word_count=1024):
    mem_a: reg32.Memory[0x0000:0x080]
    mem_b: reg32.Memory[0x0080:0x100]
    mem_c: reg32.Memory[0x0100:0x140]
    mem_d: reg32.RoMemory[0x140:0x180]

    def _config_(self):
        self.mem_b._config_(initial=Full)
        self.mem_c._config_(initial=[Unsigned[32](nr * 1024) for nr in range(16)])
        self.mem_d._config_(
            initial=[Unsigned[32](nr * 500) for nr in range(16)],
            mask_mode=reg32.Memory.MaskMode.SPLIT_WORDS,
        )


class test_axilite_reg_08(cohdl.Entity):
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
async def testbench_axilite_reg_08(dut: test_axilite_reg_08):
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

    # test mem_a (uninitialized readable and writable)

    mem_offset = 0
    for off in range(0, 0x80, 4):
        await axi_master.write_dword(mem_offset + off, 0)
        result = await axi_master.read_dword(mem_offset + off)
        assert result == 0
        rnd = rnd_data.random().as_int()
        await axi_master.write_dword(mem_offset + off, rnd)
        result = await axi_master.read_dword(mem_offset + off)
        assert result == rnd

    # test mem_b (full initialized readable and writable)

    mem_offset = 0x80
    for off in range(0, 0x80, 4):
        result = await axi_master.read_dword(mem_offset + off)
        assert result == 0xFFFFFFFF
        rnd = rnd_data.random().as_int()
        await axi_master.write_dword(mem_offset + off, rnd)
        result = await axi_master.read_dword(mem_offset + off)
        assert result == rnd

    # test mem_c (incrementing initialized readable and writable)

    mem_offset = 0x100
    for off in range(0, 0x40, 4):
        result = await axi_master.read_dword(mem_offset + off)
        assert result == (off / 4) * 1024
        rnd = rnd_data.random().as_int()
        await axi_master.write_dword(mem_offset + off, rnd)
        result = await axi_master.read_dword(mem_offset + off)
        assert result == rnd

    # test mem_c (incrementing initialized not writable)

    mem_offset = 0x140
    for off in range(0, 0x40, 4):
        result = await axi_master.read_dword(mem_offset + off)
        assert result == (off / 4) * 500
        rnd = rnd_data.random().as_int()
        await axi_master.write_dword(mem_offset + off, rnd)
        result = await axi_master.read_dword(mem_offset + off)
        assert result == (off / 4) * 500


class Unittest(unittest.TestCase):
    def test_axilite_reg_08(self):
        cohdl_testutil.run_cocotb_tests(test_axilite_reg_08, __file__, self.__module__)
