from __future__ import annotations

from cocotbext.axi import AxiLiteBus, AxiLiteMaster

import cohdl
from cohdl import Port, Bit, BitVector, Signal, Unsigned, Null
from cohdl import std

from cohdl.std.axi import axi4_light as axi


class test_axilite_02(cohdl.Entity):
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

        data_buffer = Signal[BitVector[32]](Null)

        @std.sequential(clk, reset)
        async def proc_read():
            while True:
                await axi_con.await_read_request()
                await axi_con.send_read_resp(data_buffer)
                continue

        @std.sequential(clk, reset)
        async def proc_write():
            while True:
                request = await axi_con.await_write_request()
                data_buffer.next = std.apply_mask(
                    data_buffer, request.data, std.stretch(request.strb, 8)
                )
                await axi_con.send_write_response()
                continue


import unittest
import cohdl_testutil
import cocotb


@cocotb.test()
async def testbench_axilite_02(dut: test_axilite_02):
    rnd_data = cohdl_testutil.cocotb_util.ConstrainedGenerator(32)
    rnd_mask = cohdl_testutil.cocotb_util.ConstrainedGenerator(4)

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

    for _ in range(3):
        assert (await axi_master.read_dword(0)) == 0
        buffer_value = 0

        for data, mask in zip(rnd_data.random(8), rnd_mask.random(8)):
            mask = mask.value
            data = data.value

            wide_mask = (
                (((mask & 0b0001) and 0xFF) << 0)
                | (((mask & 0b0010) and 0xFF) << 8)
                | (((mask & 0b0100) and 0xFF) << 16)
                | (((mask & 0b1000) and 0xFF) << 24)
            )

            # set store mask of axi_master, not sure if there is a better way to do this
            axi_master.write_if.strb_mask = mask

            await axi_master.write_dword(0, data)
            buffer_value = (data & wide_mask) | (buffer_value & ~wide_mask)
            assert (await axi_master.read_dword(0)) == buffer_value

        dut.reset.value = 1
        await seq.tick()
        dut.reset.value = 0


class Unittest(unittest.TestCase):
    def test_axilite_02(self):
        cohdl_testutil.run_cocotb_tests(test_axilite_02, __file__, self.__module__)
