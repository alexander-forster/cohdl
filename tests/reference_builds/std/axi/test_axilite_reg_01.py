from __future__ import annotations

from cocotbext.axi import AxiLiteBus, AxiLiteMaster

import cohdl
from cohdl import Port, Bit, BitVector, Unsigned, Null
from cohdl import std

from cohdl.std.axi import axi4_light as axi

from cohdl.std.reg import reg32


class MyRegister(reg32.Register):
    lower: reg32.Field[15:0]
    upper: reg32.MemField[31:16, Null]

    def _impl_concurrent_(self) -> None:
        self.lower <<= ~self.upper.val()


class MyRoot(reg32.AddrMap, word_count=4):
    reg_a: MyRegister[0]
    reg_b: MyRegister[4]
    reg_c: MyRegister[8]
    reg_d: MyRegister[12]


class test_axilite_reg_01(cohdl.Entity):
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
async def testbench_axilite_reg_01(dut: test_axilite_reg_01):
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

    expected_values = [0x0000FFFF] * 4

    for index in range(4):
        assert (await axi_master.read_dword(index * 4)) == expected_values[index]

    for data, index in zip(rnd_data.random(32), rnd_index.random(32)):
        data = data.value
        index = index.value

        expected_values[index] = (data & 0xFFFF0000) | ((data >> 16) ^ 0xFFFF)
        await axi_master.write_dword(index * 4, data)

        assert (await axi_master.read_dword(index * 4)) == expected_values[index]


class Unittest(unittest.TestCase):
    def test_axilite_reg_01(self):
        cohdl_testutil.run_cocotb_tests(test_axilite_reg_01, __file__, self.__module__)
