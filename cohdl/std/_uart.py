from __future__ import annotations

import cohdl
from cohdl import Bit, BitVector, Signal

from ._prescaler import Prescaler
from ._context import sequential


class UartReceiver:
    def __init__(self, clk, reset, rx, clk_div, width=8):
        self.rx = std.moving_average(clk, reset, rx, clk_div // 4, True)
        self.new_data = Signal(BitVector, width)
        self.new_data_valid = Signal(Bit, False)

        prescaler = Prescaler(clk, reset, clk_div)
        prescaler_extended = Prescaler(clk, reset, int(clk_div * 1.5))

        @std.sequential(clk, reset)
        async def proc_uart_receive():
            await (~self.rx)
            prescaler_extended.reset()
            await prescaler_extended.tick()
            prescaler.reset()

            buffer = Signal(BitVector[width])
            one_hot = Signal(BitVector[width], cohdl.Full)

            while one_hot[0]:
                one_hot <<= Bit(False) @ one_hot.msb(rest=1)
                buffer[0] <<= self.rx
                buffer.msb(rest=1).next = buffer.lsb(rest=1)
                await prescaler.tick()

            self.new_data <<= buffer
            self.new_data_valid ^= True
            await prescaler.tick()

    async def await_data(self):
        await self.new_data_valid
        return cohdl.Temporary(self.new_data)


class UartTransmitter:
    def __init__(self, clk, reset, tx, clk_div: int, width=8, stop_bits=1):
        assert stop_bits in (1, 2)

        self.tx = tx
        self.ready = Signal(Bit, False, name="uart_tx_ready")
        self.new_data = Signal(BitVector[width], name="uart_new_data")
        self.new_data_valid = Signal(Bit, False, name="uart_new_data_valid")

        prescaler = Prescaler(clk, reset, clk_div)

        @sequential(clk, reset)
        async def proc_uart_transmit():
            self.ready <<= True
            await self.new_data_valid
            self.ready <<= False
            prescaler.reset()
            buffer = Signal(self.new_data, name="uart_tx_buffer")
            one_hot = Signal(BitVector[width + 1](cohdl.Full), name="uart_tx_loop")

            # send start bit
            self.tx <<= False

            while one_hot[0]:
                if prescaler._tick:
                    one_hot <<= Bit(False) @ one_hot.msb(rest=1)
                    self.tx <<= buffer[0]
                    buffer.lsb(rest=1).next = buffer.msb(rest=1)

            # send stop bit
            self.tx <<= True
            await prescaler._tick

            if stop_bits == 2:
                await prescaler._tick

    async def send_data(self, data):
        await (self.ready and not self.new_data_valid)

        self.new_data <<= data
        self.new_data_valid ^= True
