from __future__ import annotations

from cohdl._core import (
    Bit,
    BitVector,
    Signal,
    Unsigned,
    Null,
    Full,
)

from ._context import Context, Duration, concurrent_eval
from .utility import (
    is_qualified,
    instance_check,
    InShiftRegister,
    OutShiftRegister,
    ToggleSignal,
    max_int,
    as_bitvector,
)

from ._prefix import prefix


class SpiMode:
    def __init__(self, cpol: bool, cpha: bool):
        self.cpol = cpol
        self.cpha = cpha

    @staticmethod
    def mode(val: int):
        assert val in (0, 1, 2, 3)
        return SpiMode(cpol=val // 2, cpha=val % 2)


class Spi:
    def __init__(
        self,
        sclk: Signal[Bit],
        mosi: Signal[Bit] | Signal[BitVector],
        miso: Signal[Bit] | Signal[BitVector],
        chip_select: Signal[Bit] | Signal[BitVector],
        mode: SpiMode | None = None,
    ):
        if mode is None:
            mode = SpiMode.mode(0)

        self.sclk = sclk
        self.mosi = mosi
        self.miso = miso
        self.chip_select = chip_select
        self.mode = mode


class _SpiTransaction:
    def __init__(self, master: SpiMaster):
        self._master = master

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._master._end_transaction()

    async def read_data(self, len: int):
        return self._master._read_data(len)


class SpiMaster:
    def __init__(self, ctx: Context, spi: Spi, clk_period: Unsigned | int | Duration):
        self._prefix = prefix("spi")

        with self._prefix:
            if is_qualified(clk_period):
                assert instance_check(clk_period, Unsigned)
                half_period = Signal[Unsigned.upto(max_int(clk_period))]()
                concurrent_eval(half_period, lambda: clk_period >> 1)
            else:
                if isinstance(clk_period, Duration):
                    half_period = clk_period / 2
                else:
                    half_period = clk_period // 2

            self.spi = spi

            self._toggle = ToggleSignal(
                ctx,
                half_period,
                require_enable=True,
                default_state=spi.mode.cpol,
                first_state=spi.mode.cpol ^ spi.mode.cpha,
            )

            concurrent_eval(self.spi.sclk, self._toggle.state)

    def _shift_edge(self):
        if self.spi.mode.cpol == self.spi.mode.cpha:
            return self._toggle.rising()
        else:
            return self._toggle.falling()

    def _sample_edge(self):
        if self.spi.mode.cpol == self.spi.mode.cpha:
            return self._toggle.falling()
        else:
            return self._toggle.rising()

    def _start_transaction(self, cs: Bit | BitVector | None):
        if cs is None:
            assert instance_check(self.spi.chip_select, Bit)
            self.spi.chip_select <<= False
        else:
            self.spi.chip_select <<= cs

        self._toggle.enable()

    def _end_transaction(self):
        self._toggle.disable()
        self.spi.chip_select <<= Full

    async def _send_data(self, data: BitVector):
        data_tx = OutShiftRegister(data)

        shift_width = (
            None if instance_check(self.spi.mosi, Bit) else self.spi.mosi.width
        )

        self.spi.mosi <<= data_tx.shift(shift_width)

        if self.spi.mode.cpha:
            await self._sample_edge()

        while not data_tx.empty():
            await self._shift_edge()
            self.spi.mosi <<= data_tx.shift(shift_width)

        await self._shift_edge()
        self.spi.mosi <<= Null

    async def _read_data(self, len: int):
        data_rx = InShiftRegister(len)

        while not data_rx.full():
            await self._sample_edge()
            data_rx.shift(self.spi.miso)

        return data_rx.data()

    async def transaction(
        self,
        send_data,
        receive_len: int | None = None,
        cs: Bit | BitVector | None = None,
    ):
        self._start_transaction(cs)

        await self._send_data(as_bitvector(send_data))

        if receive_len is None:
            result = await self._read_data(receive_len)
        else:
            result = None

        self._end_transaction()

        return result

    async def transaction_context(
        self, send_data, cs: Bit | BitVector | None = None
    ) -> _SpiTransaction:
        self._start_transaction(cs)
        await self._send_data(as_bitvector(send_data))
        return _SpiTransaction(self)
