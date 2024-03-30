from cohdl._core import Bit, BitVector, Unsigned, Signal, coroutine_step

from ._prefix import prefix, name
from ._context import SequentialContext, Duration
from .utility import (
    SyncFlag,
    ClockDivider,
    OutShiftRegister,
    InShiftRegister,
    debounce,
    wait_for,
)

from ._core_utility import parity as std_parity

import enum


class Baud(enum.IntEnum):
    BAUD_110 = 110
    BAUD_300 = 300
    BAUD_600 = 600
    BAUD_1200 = 1200
    BAUD_2400 = 2400
    BAUD_4800 = 4800
    BAUD_9600 = 9600
    BAUD_14400 = 14400
    BAUD_19200 = 19200
    BAUD_38400 = 38400
    BAUD_57600 = 57600
    BAUD_115200 = 115200
    BAUD_128000 = 128000


class Parity(enum.Enum):
    NONE = enum.auto()
    EVEN = enum.auto()
    ODD = enum.auto()


class UartSender:
    def __init__(
        self,
        ctx: SequentialContext,
        tx: Bit,
        baud: int | Baud,
        bits: int = 8,
        stop_bits: int = 1,
        parity: Parity = Parity.NONE,
    ):
        assert parity is Parity.NONE, "support for parity not yet implemented"

        with prefix("uarttx"):
            self._flag = SyncFlag()
            self._data = Signal[BitVector[bits]]()

            ticks_per_bit = Duration.seconds(1 / baud).count_periods(
                ctx.clk().period(), allowed_delta=0.001
            )
            bit_clk = ClockDivider(ctx, ticks_per_bit)

            async def proc_impl():
                nonlocal tx
                tx <<= True

                async with self._flag:
                    tx <<= False
                    shift_reg = OutShiftRegister(self._data)

                    while not shift_reg.empty():
                        tx <<= shift_reg.shift()

                    tx <<= True
                    await wait_for(stop_bits)

            @ctx
            def proc():
                if bit_clk.rising():
                    coroutine_step(proc_impl())

    async def send(self, data):
        assert not self._flag.is_set()
        self._data <<= data
        self._flag.set()
        await self._flag.is_clear()


_debounce_fn = debounce


class UartReceiver:
    def __init__(
        self,
        ctx: SequentialContext,
        rx: Bit,
        baud: int | Baud,
        bits: int = 8,
        stop_bits=1,
        debounce: float | None = None,
        parity: Parity = Parity.NONE,
    ):
        assert parity is Parity.NONE, "support for parity not yet implemented"

        has_parity = parity not in (None, Parity.NONE)
        parity_bit_cnt = 1 if has_parity else 0

        with prefix("uartrx"):
            if has_parity:
                parity_bit = Signal[Bit](False, name=name("parity"))

            bit_time = Duration.seconds(1.0 / baud)

            ticks_per_bit = bit_time.count_periods(
                ctx.clk().period(), allowed_delta=0.001
            )

            bit_clk = ClockDivider(ctx, ticks_per_bit, require_enable=True)

            if debounce is None:
                self._rx = rx
            else:
                assert 0.0 < debounce < 1.0, "debounce must be in the range 0-1"
                debounce_ticks = int(ticks_per_bit * debounce)
                assert debounce_ticks > 0, "debounce parameter to small"

                self._rx = _debounce_fn(
                    ctx, rx, debounce_ticks, initial=True, allowed_delta=0.01
                )

            self._flag = SyncFlag()
            self._data = Signal[BitVector[bits]]()

            received = InShiftRegister(1 + bits + parity_bit_cnt + stop_bits)
            active = Signal[Bit](False)

            bit_counter = Signal[Unsigned.upto(ticks_per_bit)](0)

            @ctx
            def proc_counter():
                if active:
                    if bit_counter == 0:
                        bit_counter.next = ticks_per_bit
                    else:
                        bit_counter.next = bit_counter - 1
                else:
                    bit_counter.next = 0

            @ctx
            def proc_clkgen():
                if not active:
                    if not self._rx:
                        bit_clk.enable()
                        active.next = True
                else:
                    if received.full():
                        bit_clk.disable()
                        active.next = False

                        if parity is Parity.NONE:
                            self._data <<= (
                                received.data().msb(rest=1).lsb(rest=stop_bits)
                            )
                            self._flag.set()
                        else:
                            p = std_parity(
                                received.data().msb(rest=1).lsb(rest=stop_bits)
                            )
                            data = (
                                received.data()
                                .msb(rest=1)
                                .lsb(rest=stop_bits + parity_bit_cnt)
                            )

                            if parity is Parity.EVEN:
                                if not p:
                                    self._data <<= data
                                    self._flag.set()
                            elif parity is Parity.ODD:
                                if p:
                                    self._data <<= data
                                    self._flag.set()

            @ctx
            def proc_receiver():
                if active:
                    if bit_counter == ticks_per_bit // 2:
                        received.shift(self._rx)
                else:
                    received.clear()

    def data_valid(self):
        return self._flag.is_set()

    def clear_data(self):
        self._flag.clear()

    def data(self):
        return self._data

    async def receive(self):
        async with self._flag:
            return self._data.copy()


class Uart:
    def __init__(
        self,
        ctx: SequentialContext,
        rx: Bit,
        tx: Bit,
        baud: int | Baud,
        bits: int = 8,
        stop_bits=1,
        debounce: float | None = None,
        parity: Parity = Parity.NONE,
    ):
        self.receiver = UartReceiver(
            ctx,
            rx=rx,
            baud=baud,
            bits=bits,
            stop_bits=stop_bits,
            debounce=debounce,
            parity=parity,
        )

        self.sender = UartSender(
            ctx, tx=tx, baud=baud, bits=bits, stop_bits=stop_bits, parity=parity
        )
