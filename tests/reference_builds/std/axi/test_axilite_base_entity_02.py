from __future__ import annotations

from cocotbext.axi import AxiLiteBus, AxiLiteMaster

from cohdl import BitVector, Null
from cohdl import std

from cohdl.std.axi import axi4_light as axi
import typing
import os

data_width = eval(os.getenv("cohdl_test_data_width", "None"))
addr_width = eval(os.getenv("cohdl_test_addr_width", "None"))


def gen_entity():

    class test_axilite_base_02_inner(
        axi.base_entity(addr_width=addr_width, data_width=data_width)
    ):

        def architecture(self):
            axi_con = self.interface_connection()
            axi_ctx = self.interface_context()

            fifo = std.Fifo[BitVector[data_width], 16]()

            @axi_ctx
            async def proc_write():
                request = await axi_con.await_write_request()

                if not fifo.full():
                    if data_width >= addr_width:
                        combined = request.data ^ std.leftpad(request.addr, data_width)
                    else:
                        combined = request.data ^ request.addr.lsb(data_width)

                    fifo.push(combined)

                await axi_con.send_write_response()

            @axi_ctx
            async def proc_read():
                await axi_con.await_read_request()
                result = std.cond_call(fifo.empty(), lambda: Null, fifo.pop)

                await axi_con.send_read_resp(result)

    # wrap inner AXI entity because cocotb AXI functions expect
    # data width of 32
    class test_axilite_base_02(axi.base_entity()):
        def architecture(self):

            @std.concurrent
            def logic():
                test_axilite_base_02_inner(
                    axi_clk=self.axi_clk,
                    axi_reset=self.axi_reset,
                    axi_awaddr=self.axi_awaddr.lsb(addr_width),
                    axi_awprot=self.axi_awprot,
                    axi_awvalid=self.axi_awvalid,
                    axi_awready=self.axi_awready,
                    axi_wdata=self.axi_wdata.lsb(data_width),
                    axi_wstrb=self.axi_wstrb,
                    axi_wvalid=self.axi_wvalid,
                    axi_wready=self.axi_wready,
                    axi_bresp=self.axi_bresp,
                    axi_bvalid=self.axi_bvalid,
                    axi_bready=self.axi_bready,
                    axi_araddr=self.axi_araddr.lsb(addr_width),
                    axi_arprot=self.axi_arprot,
                    axi_arvalid=self.axi_arvalid,
                    axi_arready=self.axi_arready,
                    axi_rdata=self.axi_rdata.lsb(data_width),
                    axi_rresp=self.axi_rresp,
                    axi_rvalid=self.axi_rvalid,
                    axi_rready=self.axi_rready,
                )

            return super().architecture()

    return test_axilite_base_02


import unittest
import cohdl_testutil
import cocotb


@cocotb.test()
async def testbench_axilite_02(dut):
    if typing.TYPE_CHECKING:
        dut = axi.base_entity()

    seq = cohdl_testutil.cocotb_util.SequentialTest(dut.axi_clk)
    dut.axi_reset.value = 1

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
    axi_master = AxiLiteMaster(
        bus, dut.axi_clk, dut.axi_reset, reset_active_level=False
    )

    gen_data = cohdl_testutil.cocotb_util.ConstrainedGenerator(data_width)
    gen_addr = cohdl_testutil.cocotb_util.ConstrainedGenerator(addr_width)

    data_mask = (1 << data_width) - 1

    for _ in range(3):
        # read from empty fifo
        assert (await axi_master.read_dword(0)) == 0
        assert (await axi_master.read_dword(0)) == 0

        for data, addr in zip(gen_data.random(4), gen_addr.random(4)):
            data = data.as_int()
            addr = addr.as_int()
            addr = addr - addr % 4

            await axi_master.write_dword(addr, data)
            expected = (data ^ addr) & data_mask
            assert (await axi_master.read_dword(addr)) == expected
            assert (await axi_master.read_dword(addr)) == 0

        data_15 = [data.as_int() for data in gen_data.random(15)]
        addr_15 = [addr.as_int() for addr in gen_addr.random(15)]
        expected_15 = []

        for data, addr in zip(data_15, addr_15):
            addr = addr - addr % 4

            expected_15.append((data ^ addr) & data_mask)
            await axi_master.write_dword(addr, data)

        # write to full buffer
        await axi_master.write_dword(0, 1)
        await axi_master.write_dword(0, 1)

        for expected in expected_15:
            assert (await axi_master.read_dword(0)) == expected

        # read from empty fifo
        assert (await axi_master.read_dword(0)) == 0
        assert (await axi_master.read_dword(0)) == 0

        dut.axi_reset.value = 0

        await seq.tick()

        dut.axi_reset.value = 1


class Unittest(unittest.TestCase):
    def test_axilite_02(self):

        global addr_width, data_width

        for addr_width in (11, 16, 32):
            for data_width in (5, 16, 32):

                cohdl_testutil.run_cocotb_tests(
                    gen_entity(),
                    __file__,
                    self.__module__,
                    extra_env={
                        "cohdl_test_addr_width": str(addr_width),
                        "cohdl_test_data_width": str(data_width),
                    },
                )
