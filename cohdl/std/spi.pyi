from __future__ import annotations

from typing import overload

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
    def mode(val: int) -> SpiMode: ...

class Spi:
    def __init__(
        self,
        sclk: Signal[Bit],
        mosi: Signal[Bit] | Signal[BitVector],
        miso: Signal[Bit] | Signal[BitVector],
        chip_select: Signal[Bit] | Signal[BitVector],
        mode: SpiMode | None = None,
    ): ...

class _SpiTransaction:
    def __init__(self, master: SpiMaster): ...
    def __enter__(self):
        return self
    def __exit__(self, type, value, traceback):
        self._master._end_transaction()
    async def read_data(self, len: int) -> BitVector: ...

class SpiMaster:
    def __init__(
        self, ctx: Context, spi: Spi, clk_period: Unsigned | int | Duration
    ): ...
    @overload
    async def transaction(
        self, send_data, receive_len: int, cs: Bit | BitVector | None = None
    ) -> BitVector: ...
    @overload
    async def transaction(
        self, send_data, cs: Bit | BitVector | None = None
    ) -> None: ...
    async def transaction_context(
        self, send_data, cs: Bit | BitVector | None = None
    ) -> _SpiTransaction: ...
