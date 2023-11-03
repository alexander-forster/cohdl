from cohdl._core import (
    Bit,
    BitVector,
    Signal,
    Null,
)


class BitwiseCrc:
    def __init__(self, poly: BitVector, initial_value=Null, invert_result=False):
        self._invert_result = invert_result
        self._poly = poly.bitvector
        self._initial_value = initial_value
        self._reg = Signal[BitVector[poly.width]](initial_value)

    def _calc_steps(self, prev: BitVector, *data: Bit):
        first, *rest = data

        cond = prev.msb() ^ first
        shifted = prev.lsb(rest=1) @ Bit(0)
        result = (shifted ^ self._poly) if cond else shifted

        if len(rest) == 0:
            return result
        else:
            return self._calc_steps(result, *rest)

    def clear(self):
        self._reg <<= self._initial_value

    def update(self, data: Bit):
        cond = self._reg.msb() ^ data
        shifted = self._reg.lsb(rest=1) @ Bit(0)
        self._reg <<= (shifted ^ self._poly) if cond else shifted

    def update_multiple(self, *data: Bit):
        self._reg <<= self._calc_steps(self._reg, *data)

    def result(self):
        if self._invert_result:
            return ~self._reg
        else:
            return self._reg.copy()
