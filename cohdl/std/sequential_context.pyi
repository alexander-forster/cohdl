from __future__ import annotations

from typing import Callable

import cohdl
from cohdl import Signal, Bit

class SeqContext:
    def __init__(self, clk: cohdl.std.Clock, reset: cohdl.std.Reset | None = None):
        self.clk: cohdl.std.Clock
        self.reset: cohdl.std.Reset | None
    def __call__(self, fn) -> None: ...
    def signal_falling(self, sig: Signal[Bit]) -> Signal[Bit]: ...
    def signal_rising(self, sig: Signal[Bit]) -> Signal[Bit]: ...
    def true_for(self, clk_cnt: int, cond: Signal | Callable) -> Signal[Bit]: ...
    def interval(self, cnt: int) -> Signal[Bit]: ...
    def moving_average(
        self,
        signal: Signal,
        sample_cnt: int,
        default=False,
    ) -> Signal[Bit]: ...
