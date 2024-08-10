from __future__ import annotations

from cocotbext.axi import AxiLiteBus, AxiLiteMaster

import cohdl
from cohdl import Port, Signal, Bit, BitVector, Unsigned, Signed, Null, Full
from cohdl import std

from cohdl.std.axi import axi4_light as axi

from cohdl.std.reg import reg32
import random

random.seed(1234)

content_mem_a = [random.randint(0, 2**32 - 1) for _ in range(64)]
content_mem_b = [random.randint(0, 2**32 - 1) for _ in range(64)]

content_mem_a[0] = 0x33221100
content_mem_a[1] = 0x77665544
content_mem_a[2] = 0x13121110
content_mem_a[3] = 0x23222120


class MyRoot(reg32.AddrMap):
    mem_a: reg32.Memory[0x0000:0x100]
    mem_b: reg32.Memory[0x0100:0x200]

    def _config_(self):
        MaskMode = reg32.Memory.MaskMode

        self.mem_a._config_(
            initial=[Unsigned[32](elem) for elem in content_mem_a],
            mask_mode=MaskMode.SPLIT_WORDS,
            allow_unaligned=True,
        )
        self.mem_b._config_(
            initial=[Unsigned[32](elem) for elem in content_mem_b],
            noreset=True,
            mask_mode=MaskMode.SPLIT_WORDS,
            allow_unaligned=True,
        )


class MemRegion:
    def __init__(self, content, start, end, noreset, maskable):
        self._content = content
        self._data = list(content)

        self.start = start
        self.end = end
        self.noreset = noreset
        self.maskable = maskable

    def contains_addr(self, addr):
        return self.start <= addr < self.end

    def reset(self):
        if not self.noreset:
            self._data = list(self._content)

    def write(self, addr, data, mask):
        addr = (addr - self.start) // 4

        if self.maskable:
            self._data[addr] = (self._data[addr] & ~mask) | (data & mask)
        else:
            self._data[addr] = data

    def read(self, addr):
        addr = (addr - self.start) // 4
        return self._data[addr]


class MemMock:
    def __init__(self):
        self._memories = [
            MemRegion(
                content_mem_a, start=0x000, end=0x100, noreset=False, maskable=True
            ),
            MemRegion(
                content_mem_b, start=0x100, end=0x200, noreset=True, maskable=True
            ),
        ]

    def reset(self):
        for mem in self._memories:
            mem.reset()

    def write(self, addr, data, mask):
        for mem in self._memories:
            if mem.contains_addr(addr):
                mem.write(addr, data, mask)

    def write_unaligned(self, addr, data):
        match addr % 4:
            case 0:
                self.write(addr, data, 0xFFFFFFFF)
            case 1:
                self.write(addr - 1, data << 8, 0xFFFFFF00)
                self.write(addr + 3, data >> 24, 0x000000FF)
            case 2:
                self.write(addr - 2, data << 16, 0xFFFF0000)
                self.write(addr + 2, data >> 16, 0x0000FFFF)
            case 3:
                self.write(addr - 3, data << 24, 0xFF000000)
                self.write(addr + 1, data >> 8, 0x00FFFFFF)

    def read(self, addr):
        for mem in self._memories:
            if mem.contains_addr(addr):
                return mem.read(addr)
        return 0

    def read_unaligned(self, addr):
        match addr % 4:
            case 0:
                return self.read(addr)
            case 1:
                low = self.read(addr - 1) & 0xFFFFFF00
                high = self.read(addr + 3) & 0x000000FF
                return (low >> 8) | (high << 24)
            case 2:
                low = self.read(addr - 2) & 0xFFFF0000
                high = self.read(addr + 2) & 0x0000FFFF
                return (low >> 16) | (high << 16)
            case 3:
                low = self.read(addr - 3) & 0xFF000000
                high = self.read(addr + 1) & 0x00FFFFFF
                return (low >> 24) | (high << 8)


class test_axilite_reg_10(cohdl.Entity):
    clk = Port.input(Bit)
    reset = Port.input(Bit)

    addr_offset = Port.input(Unsigned[2])

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

        # cocotb.axi splits unaligned accesses into multiple aligned ones
        # to test unaligned access anyway we introduce a separate offset
        unaligned_awaddr = Signal[Unsigned[32]]()
        unaligned_araddr = Signal[Unsigned[32]]()

        @std.concurrent
        def logic():
            # cocotb.axi assumes that the two lsbs are ignored
            # since our unaligned memory uses them we mask them here
            mask = ~Unsigned[32](3)

            unaligned_awaddr.next = (self.axi_awaddr & mask) + self.addr_offset
            unaligned_araddr.next = (self.axi_araddr & mask) + self.addr_offset

        axi_con = axi.Axi4Light(
            clk=clk,
            reset=reset,
            wraddr=axi.Axi4Light.WrAddr(
                valid=self.axi_awvalid,
                ready=self.axi_awready,
                awaddr=unaligned_awaddr,
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
                araddr=unaligned_araddr,
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
async def testbench_axilite_reg_10(dut: test_axilite_reg_10):

    seq = cohdl_testutil.cocotb_util.SequentialTest(dut.clk)

    dut.addr_offset.value = 0
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
    dut.addr_offset.value = 0

    bus = AxiLiteBus.from_prefix(dut, "axi")
    axi_master = AxiLiteMaster(bus, dut.clk)

    mock = MemMock()

    await seq.delta()

    def crosses_boundary(addr):
        return (addr < 0x100 and addr + 4 > 0x100) or (addr + 4 > 0x200)

    for outer in range(3):
        for inner in range(128):
            addr = random.randint(0, 0x200)

            if crosses_boundary(addr):
                continue

            addr_off = addr % 4
            addr_aligned = addr - addr_off

            dut.addr_offset.value = addr_off
            await seq.delta()

            expected = mock.read_unaligned(addr)
            result = await axi_master.read_dword(addr_aligned)

            assert (
                result == expected
            ), f"{outer}:{inner} at addr = {addr:04x} | {expected:08x} != {result:08x}"

        for inner in range(128):
            addr = random.randint(0, 0x200)

            if crosses_boundary(addr):
                continue

            addr_off = addr % 4
            addr_aligned = addr - addr_off

            data = random.randint(0, 2**32 - 1)

            dut.addr_offset.value = addr_off
            await seq.delta()

            mock.write_unaligned(addr, data)
            await axi_master.write_dword(addr_aligned, data)

            expected = mock.read_unaligned(addr)
            result = await axi_master.read_dword(addr_aligned)

            assert (
                result == expected
            ), f"{outer}:{inner} at addr = {addr:04x} | {expected:08x} != {result:08x}"

            #
            # check, that aligned access with mask still works
            #

            dut.addr_offset.value = 0
            await seq.delta()
            data = random.randint(0, 2**32 - 1)

            mock.write_unaligned(addr, data)
            await axi_master.write_dword(addr, data)

            expected = mock.read_unaligned(addr)
            result = await axi_master.read_dword(addr)

            assert (
                result == expected
            ), f"{outer}:{inner} at addr = {addr:04x} | {expected:08x} != {result:08x}"

            continue

        dut.reset.value = 1
        await seq.tick()
        dut.reset.value = 0
        await seq.tick()
        mock.reset()


class Unittest(unittest.TestCase):
    def test_axilite_reg_10(self):
        cohdl_testutil.run_cocotb_tests(test_axilite_reg_10, __file__, self.__module__)

    def test_rdl_writer(self):
        from cohdl.std.reg.system_rdl import to_system_rdl
        import tempfile

        with tempfile.NamedTemporaryFile("w") as file:
            print(to_system_rdl(MyRoot), file=file)
