from __future__ import annotations

from cocotbext.axi import AxiLiteBus, AxiLiteMaster

import cohdl
from cohdl import Port, Bit, BitVector, Signal, Unsigned, Null
from cohdl import std

from cohdl.std.axi import axi4_light as axi
import typing

#
#
#


def gen_entity():

    class test_axilite_base_01(axi.base_entity()):

        def architecture(self):
            axi_con = self.interface_connection()
            axi_ctx = self.interface_context()

            data_buffer = Signal[BitVector[32]](Null)

            @axi_ctx
            async def proc_read():
                await axi_con.await_read_request()
                await axi_con.send_read_resp(data_buffer)

            @axi_ctx
            async def proc_write():
                request = await axi_con.await_write_request()
                data_buffer.next = request.data
                await axi_con.send_write_response()

    return test_axilite_base_01


import unittest
import cohdl_testutil
import cocotb


@cocotb.test()
async def testbench_axilite_01(dut):
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

    for _ in range(3):
        assert (await axi_master.read_dword(0)) == 0

        for data in range(8):
            await axi_master.write_dword(0, data)
            assert (await axi_master.read_dword(0)) == data

        dut.axi_reset.value = 0
        await seq.tick()
        dut.axi_reset.value = 1


class Unittest(unittest.TestCase):
    def test_axilite_01(self):

        cohdl_testutil.run_cocotb_tests(gen_entity(), __file__, self.__module__)
