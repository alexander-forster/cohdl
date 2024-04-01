from __future__ import annotations

from cocotbext.axi import AxiLiteBus, AxiLiteMaster

import cohdl
from cohdl import Port, Signal, Bit, BitVector, Unsigned, Signed, Null, Full
from cohdl import std

from cohdl.std.axi import axi4_light as axi

from cohdl.std.reg import reg32


class ExamplePush(reg32.Register):
    data: reg32.MemField[15:0, Null]
    rd_cnt: reg32.UField[23:16, Null]
    wr_cnt: reg32.UField[31:24, Null]

    rd_notification: reg32.PushOnNotify.Read
    wr_notification: reg32.PushOnNotify.Write

    def _impl_sequential_(self):
        if self.rd_notification:
            # self.rd_notification is true for one clock cycle after each
            # read from the current register
            self.rd_cnt <<= self.rd_cnt.val() + 1
        if self.wr_notification:
            # self.wr_notification is true for one clock cycle after each
            # write to the current register
            self.wr_cnt <<= self.wr_cnt.val() + 1


class ExampleFlag(reg32.Register):
    data_a: reg32.MemField[7:0, Null]
    data_b: reg32.MemUField[11:8, Null]
    data_c: reg32.MemSField[15:12, Null]
    rd_cnt: reg32.UField[23:16, Null]

    rd_notification: reg32.FlagOnNotify.Read

    async def _impl_sequential_(self):
        # wait for notification, then increment
        # the read counter register
        async with self.rd_notification:
            self.rd_cnt <<= self.rd_cnt.val() + 1


class MyReg(reg32.Register):
    read_cnt_1: reg32.UField[7:0]
    read_cnt_2: reg32.UField[15:8]
    write_cnt_1: reg32.UField[23:16]
    write_cnt_2: reg32.UField[31:24, 0]

    notify_push_read: reg32.PushOnNotify.Read
    notify_flag_read: reg32.FlagOnNotify.Read
    notify_push_write: reg32.PushOnNotify.Write
    notify_flag_write: reg32.FlagOnNotify.Write

    def _impl_(self, ctx: std.SequentialContext) -> None:
        read_1 = Signal[Unsigned[8]](Null)
        read_2 = Signal[Unsigned[8]](Null)
        write_1 = Signal[Unsigned[8]](Null)
        write_2 = Signal[Unsigned[8]](Null)

        @std.concurrent
        def logic():
            self.read_cnt_1 <<= read_1
            self.read_cnt_2 <<= read_2
            self.write_cnt_1 <<= write_1

        @ctx
        def proc_read_cnt_1():
            if self.notify_push_read:
                read_1.next = read_1 + 1

        @ctx
        async def proc_read_cnt_2():
            nonlocal read_2
            async with self.notify_flag_read:
                read_2 <<= read_2 + 1

        @ctx
        def proc_write_cnt_1():
            if self.notify_push_write:
                write_1.next = write_1 + 1

        @ctx
        async def proc_write_cnt_2():
            nonlocal write_2

            await cohdl.expr(bool(self.notify_flag_write))
            self.write_cnt_2 <<= self.write_cnt_2.val() + 1
            self.notify_flag_write.clear()


class MyRoot(reg32.AddrMap, word_count=8):
    reg_a: MyReg[0]
    reg_b: MyReg[4]
    example_push: ExamplePush[8]
    example_flag: ExampleFlag[12]


class test_axilite_reg_07(cohdl.Entity):
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
async def testbench_axilite_reg_07(dut: test_axilite_reg_07):
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

    for off in (0x00, 0x04):
        assert (await axi_master.read_dword(off)) == 0x00000000
        assert (await axi_master.read_dword(off)) == 0x00000101
        assert (await axi_master.read_dword(off)) == 0x00000202
        await axi_master.write_dword(off, 0xFFFFFFFF)
        assert (await axi_master.read_dword(off)) == 0x01010303
        await axi_master.write_dword(off, 0xFFFFFFFF)
        assert (await axi_master.read_dword(off)) == 0x02020404

    assert (await axi_master.read_dword(8)) == 0x00000000
    assert (await axi_master.read_dword(8)) == 0x00010000
    await axi_master.write_dword(8, 0xFFFFFFFF)
    assert (await axi_master.read_dword(8)) == 0x0102FFFF

    assert (await axi_master.read_dword(12)) == 0x00000000
    assert (await axi_master.read_dword(12)) == 0x00010000
    await axi_master.write_dword(12, 0x12345678)
    assert (await axi_master.read_dword(12)) == 0x00025678


class Unittest(unittest.TestCase):
    def test_axilite_reg_07(self):
        cohdl_testutil.run_cocotb_tests(test_axilite_reg_07, __file__, self.__module__)
