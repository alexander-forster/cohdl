from __future__ import annotations

from typing import overload

from cohdl._core import (
    Bit,
    BitVector,
    Signal,
    Unsigned,
)

from ._context import Context, Duration, Frequency

class SpiMode:
    def __init__(self, cpol: bool, cpha: bool):
        self.cpol: bool
        self.cpha: bool
    @staticmethod
    def mode(val: int) -> SpiMode:
        """
        Constructs an instance of SpiMode with cpol and cpha set
        according to the given integer.
        """

class Spi:
    """
    a class containing all signals of an SPI interface
    and the operating mode.
    """

    def __init__(
        self,
        sclk: Signal[Bit],
        mosi: Signal[Bit] | Signal[BitVector],
        miso: Signal[Bit] | Signal[BitVector],
        chip_select: Signal[Bit] | Signal[BitVector],
        mode: SpiMode | None = None,
    ):
        """
        Collect all signals of an SPI interface alongside the operating mode.
        """

class _SpiTransaction:
    def __init__(self, master: SpiMaster): ...
    def __enter__(self) -> _SpiTransaction: ...
    def __exit__(self, type, value, traceback) -> None: ...
    async def send_data(self, data: BitVector | str) -> None:
        """
        Write send all bytes of `data` over the mosi data line.
        """
    async def read_data(self, len: int) -> BitVector:
        """
        Read `len` Bits of data from the interface.
        """

class SpiMaster:
    def __init__(
        self,
        ctx: Context,
        spi: Spi,
        *,
        clk_period: Unsigned | int | Duration | None = None,
        clk_frequency: Frequency | None = None,
    ):
        """

        One of `clk_period` and `clk_frequency` must be set. These values define
        the speed of the clock signal generated on 'spi.sclk`. Unsigned/int values
        are interpreted as ticks of the clock of `ctx` and should be dividable by two
        to allow a 50 % duty cycle.
        When a std.Frequency or std.Duration is specified, the number of clock ticks is inferred
        from the clock speed of the ctx Clock (this only works when ctx has a clock with
        a defined frequency).
        """
    @overload
    async def transaction(
        self,
        send_data: BitVector | str,
        receive_len: int,
        receive_offset: int = 0,
        cs: Bit | BitVector = Bit(0),
    ) -> BitVector:
        """
        Send `send_data` over the MOSI line of the interface. Once the last Bit was sent
        read `receive_len` from the MISO line. `cs` will be assigned to the chip select line
        it is usually a single `0` Bit or a one-cold encoded BitVector (a single bit set to zero).

        `receive_offset` determines, when data collection on the MISO line starts relative
        to the end of the transmission of send_data.
        """
    @overload
    async def transaction(
        self,
        send_data: BitVector | str,
        cs: Bit | BitVector = Bit(0),
    ) -> None:
        """
        Send `send_data` over tho MOSI line of the interface. Once the last Bit was sent
        `cs` will be assigned to the chip select line it is usually a single `0` Bit or a one-cold encoded BitVector (a single bit set to zero).
        """
    async def transaction_context(
        self,
        send_data: BitVector | str | None = None,
        cs: Bit | BitVector = Bit(0),
    ) -> _SpiTransaction:
        """
        Start to transaction context by sending `send_data` over the mosi line.
        Returns an object that can be used in a Python context manager.

        ---

        Example:

        >>> with await spi_master.transaction_context("110011") as ctx:
        >>>     # read 4 Bits into the Signal x
        >>>     x <<= await ctx.read_data(4)
        >>>     # send BitVector y
        >>>     await ctx.send_data(y)
        >>>     # read 8 more Bits into the Signal z
        >>>     z <<= await ctx.read_data(8)
        >>>
        >>> # spi transaction is automatically completed by unsetting chip select
        """
