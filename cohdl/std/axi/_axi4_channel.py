from __future__ import annotations

import cohdl

Signal = cohdl.Signal
Bit = cohdl.Bit


class Channel:
    def __init__(self, valid, ready, **kwargs):
        self.valid = valid
        self.ready = ready

        self._signals = kwargs

    @classmethod
    def signal(cls, **kwargs):
        return cls(
            Signal(Bit, False),
            Signal(Bit, False),
            **{name: Signal(val) for name, val in kwargs.items()},
        )

    async def send(self, **kwargs):
        for name, value in kwargs.items():
            self._signals[name] <<= value

        self.valid <<= True

        await self.ready

        self.valid <<= False

        for value in self._signals.values():
            value <<= cohdl.Null

    async def receive(self):
        self.ready <<= True

        await self.valid

        self.ready <<= False

        return self._signals
