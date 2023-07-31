import unittest
import random

from cohdl import Entity, Bit, BitVector, Port
from cohdl import std

from cocotbext.spi import SpiSlaveBase, SpiSignals, SpiConfig

from cohdl_testutil import cocotb_util


class test_spi_ctx_00(Entity):
    clk = Port.input(Bit)
    start_transaction = Port.input(Bit)
    command = Port.input(BitVector[8])
    led = Port.output(BitVector[8])

    sclk = Port.output(Bit)
    mosi = Port.output(Bit)
    miso = Port.input(Bit)
    cs = Port.output(Bit)

    def architecture(self):
        ctx = std.Context(std.Clock(self.clk, frequency=std.MHz(200)))

        spi = std.spi.Spi(
            sclk=self.sclk,
            mosi=self.mosi,
            miso=self.miso,
            chip_select=self.cs,
        )

        spi_master = std.spi.SpiMaster(ctx, spi, clk_frequency=std.MHz(25))

        @ctx
        async def proc():
            await self.start_transaction

            with await spi_master.transaction_context(self.command) as spi:
                self.led[7:3] <<= await spi.read_data(5)
                self.led[2:0] <<= await spi.read_data(3)


class SimpleSpiSlave(SpiSlaveBase):
    def __init__(self, signals):
        self._config = SpiConfig()
        self.content = 0
        self.data = 0
        super().__init__(signals)

    async def _transaction(self, frame_start, frame_end):
        await frame_start
        self.idle.clear()
        self.content = int(await self._shift(15, tx_word=self.data)) >> 7
        await frame_end


@cocotb_util.test()
async def testbench_spi_ctx_00(dut: test_spi_ctx_00):
    seq = cocotb_util.SequentialTest(dut.clk)
    spi_signals = SpiSignals(sclk=dut.sclk, mosi=dut.mosi, miso=dut.miso, cs=dut.cs)
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
    def test_spi_ctx_00(self):
        cocotb_util.run_cocotb_tests(test_spi_ctx_00, __file__, self.__module__)
