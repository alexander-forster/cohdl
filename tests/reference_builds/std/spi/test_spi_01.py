import unittest
import random

from cohdl import Entity, Bit, BitVector, Port
from cohdl import std

from cocotbext.spi import SpiSlaveBase, SpiBus, SpiConfig

from cohdl_testutil import cocotb_util


class test_spi_01(Entity):
    clk = Port.input(Bit)
    start_transaction = Port.input(Bit)
    command = Port.input(BitVector[8])
    led = Port.output(BitVector[8])

    sclk = Port.output(Bit)
    mosi = Port.output(Bit)
    miso = Port.input(Bit)
    cs = Port.output(Bit)

    def architecture(self):
        ctx = std.SequentialContext(std.Clock(self.clk, frequency=std.MHz(200)))

        spi = std.spi.Spi(
            sclk=self.sclk,
            mosi=self.mosi,
            miso=self.miso,
            chip_select=self.cs,
            mode=std.spi.SpiMode.mode(1),
        )

        spi_master = std.spi.SpiMaster(ctx, spi, clk_frequency=std.MHz(25))

        @ctx
        async def proc():
            await self.start_transaction
            self.led <<= await spi_master.transaction(self.command, 8)


class SimpleSpiSlave(SpiSlaveBase):
    def __init__(self, signals):
        self._config = SpiConfig(cpha=True)
        self.content = 0
        self.data = 0
        super().__init__(signals)

    async def _transaction(self, frame_start, frame_end):
        await frame_start
        self.idle.clear()
        self.content = int(await self._shift(16, tx_word=self.data)) >> 8
        await frame_end


@cocotb_util.test()
async def testbench_spi_01(dut: test_spi_01):
    seq = cocotb_util.SequentialTest(dut.clk)
    spi_signals = SpiBus(dut)
    spi_slave = SimpleSpiSlave(spi_signals)

    dut.start_transaction.value = False
    await seq.tick(100)

    for _ in range(10):
        rnd = random.randint(0, 255)
        command = random.randint(0, 255)
        spi_slave.data = rnd
        dut.command.value = command
        dut.start_transaction.value = True
        await seq.tick()
        dut.start_transaction.value = False

        for _ in range(150):
            await seq.tick()

        assert dut.led.value == rnd
        assert command == spi_slave.content


class Unittest(unittest.TestCase):
    def test_spi_01(self):
        cocotb_util.run_cocotb_tests(test_spi_01, __file__, self.__module__)
