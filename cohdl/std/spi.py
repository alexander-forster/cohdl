from __future__ import annotations

from cohdl._core import Bit, BitVector, Signal, Unsigned, Null, Full, TypeQualifierBase

from ._context import Context, Duration, Frequency, concurrent_eval, concurrent_assign
from ._core_utility import instance_check, is_qualified, as_bitvector


from .utility import (
    InShiftRegister,
    OutShiftRegister,
    ToggleSignal,
    max_int,
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

    async def send_data(self, data: BitVector | str):
        await self._master._send_data(data, _no_wait=True)

    async def read_data(self, len: int):
        return await self._master._read_data(len)


class SpiMaster:
    def __init__(
        self,
        ctx: Context,
        spi: Spi,
        *,
        clk_period: Unsigned | int | Duration | None = None,
        clk_frequency: Frequency | None = None,
    ):
        assert (
            clk_period is None or clk_frequency is None
        ), "spi clock period or frequency must be set"

        if clk_period is None:
            clk_period = clk_frequency.period()

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

            self._cs = Signal[type(TypeQualifierBase.decay(self.spi.chip_select))](Full)

            concurrent_eval(self.spi.sclk, self._toggle.state)
            concurrent_assign(self.spi.chip_select, self._cs)

    def _shift_edge(self):
        if self.spi.mode.cpol == self.spi.mode.cpha:
            return self._toggle.falling()
        else:
            return self._toggle.rising()

    def _sample_edge(self):
        if self.spi.mode.cpol == self.spi.mode.cpha:
            return self._toggle.rising()
        else:
            return self._toggle.falling()

    def _start_transaction(self, cs: Bit | BitVector | None):
        if cs is None:
            assert instance_check(self._cs, Bit)
            self._cs <<= False
        else:
            self._cs <<= cs

        self._toggle.enable()

    def _end_transaction(self):
        self._toggle.disable()
        self._cs <<= Full

    async def _send_data(self, data: BitVector, *, _no_wait=False):
        data_tx = OutShiftRegister(data, msb_first=True)

        shift_width = (
            None if instance_check(self.spi.mosi, Bit) else self.spi.mosi.width
        )

        if not _no_wait and self.spi.mode.cpha:
            await self._shift_edge()

        self.spi.mosi <<= data_tx.shift(shift_width)

        while not data_tx.empty():
            await self._shift_edge()
            self.spi.mosi <<= data_tx.shift(shift_width)

        await self._shift_edge()

        self.spi.mosi <<= Null

    async def _read_data(self, len: int):
        data_rx = InShiftRegister(len, msb_first=True)

        while not data_rx.full():
            await self._sample_edge()
            data_rx.shift(self.spi.miso)
        await self._shift_edge()
        return data_rx.data()

    async def transaction(
        self, send_data: BitVector, receive_len: int = 0, receive_offset=0, cs=None
    ):
        total_len = len(send_data) + receive_len + receive_offset
        assert not is_qualified(
            total_len
        ), "receive_len and receive_offset must be runtime constant"
        assert len(send_data) >= -receive_offset
        assert len(send_data) <= total_len

        shift_width = (
            None if instance_check(self.spi.mosi, Bit) else self.spi.mosi.width
        )

        self._start_transaction(cs)

        cnt = Signal[Unsigned.upto(total_len)](total_len)
        shift_out = OutShiftRegister(send_data, msb_first=True, unchecked=True)

        if receive_len != 0:
            shift_in = InShiftRegister(receive_len, msb_first=True, unchecked=True)

        self.spi.mosi <<= shift_out.shift(shift_width)

        while cnt:
            cnt <<= cnt - 1
            await self._sample_edge()

            if receive_len != 0:
                shift_in.shift(self.spi.miso)

            await self._shift_edge()
            self.spi.mosi <<= shift_out.shift(shift_width)

        self._end_transaction()

        if receive_len != 0:
            return shift_in.data()
        return None

    async def parallel_transaction(
        self, send_data: BitVector, shift_cnt: int | Unsigned, cs=None
    ):
        shift_width = (
            None if instance_check(self.spi.mosi, Bit) else self.spi.mosi.width
        )

        self._start_transaction(cs)

        cnt = Signal[Unsigned.upto(max_int(shift_cnt))](shift_cnt)
        shift_out = OutShiftRegister(send_data, msb_first=True, unchecked=True)
        shift_in = InShiftRegister(send_data.width, msb_first=True, unchecked=True)

        self.spi.mosi <<= shift_out.shift(shift_width)

        while cnt:
            cnt <<= cnt - 1
            await self._sample_edge()

            shift_in.shift(self.spi.miso)

            await self._shift_edge()
            self.spi.mosi <<= shift_out.shift(shift_width)

        self._end_transaction()

        return shift_in.data()

    async def transaction_context(
        self, send_data=None, cs: Bit | BitVector | None = None
    ) -> _SpiTransaction:
        self._start_transaction(cs)

        if send_data is not None:
            await self._send_data(as_bitvector(send_data))
        return _SpiTransaction(self)
