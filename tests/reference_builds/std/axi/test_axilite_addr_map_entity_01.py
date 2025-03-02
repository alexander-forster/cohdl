from __future__ import annotations

from cocotbext.axi import AxiLiteBus, AxiLiteMaster

import cohdl
from cohdl import Port, Bit, BitVector, Signal, Unsigned, Null
from cohdl import std

from cohdl.std.reg.reg import reg32
from cohdl.std.reg.system_rdl import to_system_rdl
from cohdl.std.axi import axi4_light as axi

from typing import Self


class RegReverse(reg32.Register):
    data: reg32.MemField[31:0]

    def _on_read_(self):
        return self(data=std.reverse_bits(self.data.val()))


class RegWrCnt(reg32.Register):
    data: reg32.MemUField[31:0, Null]

    def _on_write_(self, inp: Self):
        return self(data=self.data.val() + 1)


class RegRdCnt(reg32.Register):
    data: reg32.UField[31:0]

    def _config_(self):
        self._counter = Signal[Unsigned[32]](0)

    def _impl_concurrent_(self):
        self.data <<= self._counter

    def _on_read_(self):
        self._counter <<= self._counter + 1
        return self


class test_axilite_addr_map_entity_01(axi.addr_map_entity()):
    # check that addr_map_entities can be defined
    # using register annotations

    word_0: reg32.MemWord[0x00]
    word_1: reg32.MemWord[0x04]
    word_2: reg32.MemWord[0x08]
    word_3: reg32.MemWord[0x0C]

    reg_reverse: RegReverse[0x10]

    reg_cnt_wr: RegWrCnt[0x20]
    reg_cnt_rd: RegRdCnt[0x24]


#
#
#

import unittest
import cohdl_testutil
import cocotb


@cocotb.test()
async def testbench_axilite_01(dut: test_axilite_addr_map_entity_01):

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

    datagen = cohdl_testutil.cocotb_util.ConstrainedGenerator(32)

    for _ in range(3):
        assert (await axi_master.read_dword(0)) == 0

        for addr in (0x00, 0x04, 0x08, 0x0C):
            for data in datagen.random(8):
                data = data.as_int()
                await axi_master.write_dword(addr, data)
                assert (await axi_master.read_dword(addr)) == data

        for data in datagen.random(8):
            reverse = int(data.as_str()[::-1], base=2)

            await axi_master.write_dword(0x10, data.as_int())
            assert (await axi_master.read_dword(0x10)) == reverse

        for cnt in range(8):
            assert (await axi_master.read_dword(0x20)) == cnt
            await axi_master.write_dword(0x20, 0x00)

            assert (await axi_master.read_dword(0x24)) == cnt

        dut.axi_reset.value = 0
        await seq.tick()
        dut.axi_reset.value = 1


class Unittest(unittest.TestCase):
    def test_axilite_01(self):

        cohdl_testutil.run_cocotb_tests(
            test_axilite_addr_map_entity_01, __file__, self.__module__
        )

    def test_system_rdl(self):
        # basic test, checks that conversion to system rdl does not crash
        # output not verified
        to_system_rdl(test_axilite_addr_map_entity_01._gen_addr_map_())
