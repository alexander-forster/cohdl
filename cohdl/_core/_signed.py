from __future__ import annotations

from ._bit_vector import BitVector, BitOrder
from ._integer import Integer

from ._intrinsic import _intrinsic
from cohdl.utility import Span


class Signed(BitVector):
    _SubTypes = {}

    @staticmethod
    @_intrinsic
    def _int_to_binary(width: int, number: int) -> str:
        return "".join([str(int(bool(number & 2**i))) for i in range(width)])[::-1]

    @staticmethod
    @_intrinsic
    def from_int(
        default: int | Integer,
        max: int | None = None,
        min: int | None = None,
        order: BitOrder = BitOrder.DOWNTO,
    ):
        if isinstance(default, Integer):
            default = default.get_value()

        if min is None:
            min = -abs(default)

        if max is None:
            max = abs(default)

        assert min <= default <= max

        width_neg = len(bin(abs(min) - 1)) - 2 - (min == 0)
        width_pos = len(bin(max)) - 2

        width = width_pos if width_neg < width_pos else width_neg

        return Signed[width + 1](default)

    @_intrinsic
    def __init__(
        self,
        val: None | BitVector | str | int = None,
    ):
        if isinstance(val, Integer):
            val = int(val)

        if isinstance(val, int):
            assert (-(2 ** (self.width - 1))) <= val < 2 ** (self.width - 1)
            val = Signed._int_to_binary(self.width, val)

        super().__init__(val)

    @_intrinsic
    def pow_2(self, exp: int) -> Signed:
        if exp == 0:
            return Signed(self.width(), self, self._order)

        if exp > 0:
            return (self.as_bitvector() @ BitVector.zeros(exp)).as_signed()

        if exp >= self.width():
            return Signed(1, 0)

        return self.msb(self.width - exp).as_signed()

    @_intrinsic
    def min(self) -> int:
        return -(2 ** (self.width - 1))

    @_intrinsic
    def max(self) -> int:
        return 2 ** (self.width - 1) - 1

    @_intrinsic
    def _assign(self, other) -> None:
        import cohdl

        if isinstance(other, Integer):
            other = int(other)

        if isinstance(other, int):
            assert self.min() <= other <= self.max()

            if other < 0:
                binary = Span([*bin(abs(other + 1))[2:][::-1]]).generate(
                    lambda char: "0" if char == "1" else "1"
                )
                self._value.apply_zip(
                    lambda bit, char: bit._assign(char), binary.iter_extend("1")
                )
            else:
                binary = Span([*bin(other)[2:][::-1]])
                self._value.apply_zip(
                    lambda bit, char: bit._assign(char), binary.iter_extend("0")
                )
        elif isinstance(other, Signed):
            assert self.width >= other.width
            self._assign(other.to_int())
        elif isinstance(other, cohdl.Unsigned):
            assert self.width > other.width
            self._assign(other.to_int())
        elif (
            isinstance(other, (BitVector, str))
            or other is cohdl.Null
            or other is cohdl.Full
        ):
            super()._assign(other)
        else:
            raise AssertionError()

    @_intrinsic
    def to_int(self) -> int:
        result = 0

        for shift, bit in enumerate(self._value):
            if bit:
                result |= 1 << shift

        if self.msb():
            result -= 2**self.width

        return result

    @_intrinsic
    def add(self, rhs: Signed | int | Integer, target_width=None) -> Signed:
        if isinstance(rhs, Integer):
            rhs = rhs.get_value()

        if isinstance(rhs, int):
            rhs = Signed.from_int(rhs, order=self._order)

            if target_width is None:
                # adding integer, that cannot be represented
                # without explicit specification of target_width
                # is probably an error
                assert rhs.width() <= self.width()
                target_width = self.width()
        else:
            assert isinstance(rhs, Signed)
            assert self.order == rhs.order

            if target_width is None:
                target_width = max(self.width, rhs.width)

        target = Signed[target_width](0)

        carry = False

        sign_a = self._value[-1]
        sign_b = rhs._value[-1]

        for a, b, t in zip(
            self._value.iter_extend(sign_a),
            rhs._value.iter_extend(sign_b),
            target._value,
        ):
            a = bool(a)
            b = bool(b)

            t._assign((a + b + carry) & 1)
            carry = (a + b + carry) > 1

        return target

    @_intrinsic
    def sub(self, rhs: Signed | int | Integer, target_width=None) -> Signed:
        if isinstance(rhs, Integer):
            rhs = rhs.get_value()

        rhs = -rhs
        return self.add(rhs, target_width)

    @_intrinsic
    def __add__(self, rhs: Signed | int | Integer) -> Signed:
        if isinstance(rhs, Integer):
            rhs = rhs.get_value()

        if isinstance(rhs, int):
            rhs = Signed.from_int(rhs)

        if not isinstance(rhs, Signed):
            return NotImplemented

        return self.add(rhs)

    @_intrinsic
    def __radd__(self, lhs: int | Integer) -> Signed:
        if isinstance(lhs, Integer):
            lhs = lhs.get_value()

        return self.add(lhs)

    @_intrinsic
    def __sub__(self, rhs: Signed | int | Integer) -> Signed:
        if isinstance(rhs, Integer):
            rhs = rhs.get_value()

        if not isinstance(rhs, Signed):
            return NotImplemented

        return self.sub(rhs)

    @_intrinsic
    def __rsub__(self, lhs: int | Integer) -> Signed:
        if isinstance(lhs, Integer):
            lhs = lhs.get_value()

        return lhs + -self

    @_intrinsic
    def __mul__(self, rhs: Signed | int | Integer) -> Signed:
        result_width = self.width

        if isinstance(rhs, Signed):
            result_width = self.width + rhs.width
            rhs = rhs.to_int()
        elif isinstance(rhs, Integer):
            rhs = rhs.get_value()

        lhs = self.to_int()

        return Signed[result_width](lhs * rhs)

    @_intrinsic
    def __floordiv__(self, rhs: Signed | int | Integer) -> Signed:
        result_width = self.width

        if isinstance(rhs, Signed):
            rhs = rhs.to_int()
        elif isinstance(rhs, Integer):
            rhs = rhs.get_value()

        lhs = self.to_int()

        if rhs == 0:
            return Signed[result_width]()
        return Signed[result_width](lhs // rhs)

    @_intrinsic
    def __mod__(self, rhs: Signed | int | Integer) -> Signed:
        result_width = self.width

        if isinstance(rhs, Signed):
            rhs = rhs.to_int()
        elif isinstance(rhs, Integer):
            rhs = rhs.get_value()

        lhs = self.to_int()

        if rhs == 0:
            return Signed[result_width]()
        return Signed[result_width](lhs % rhs)

    @_intrinsic
    def __lshift__(self, rhs) -> Signed:
        width = self.width
        val = (self.to_int() << int(rhs)) & ((1 << width) - 1)

        if val & (1 << (width - 1)):
            val = val - (1 << (width))

        return Signed[self.width](val)

    @_intrinsic
    def __rshift__(self, rhs) -> Signed:
        val = self.to_int() >> int(rhs)
        return Signed[self.width](val)

    @_intrinsic
    def __neg__(self) -> Signed:
        return ~self + 1

    @_intrinsic
    def __eq__(self, other: BitVector | int | Integer) -> bool:
        if isinstance(other, Integer):
            other = other.get_value()

        if isinstance(other, int):
            return bool(other == self.to_int())
        return super().__eq__(other)

    @_intrinsic
    def __ne__(self, other: BitVector | int | Integer) -> bool:
        if isinstance(other, Integer):
            other = other.get_value()

        if isinstance(other, int):
            return bool(other != self.to_int())
        return super().__ne__(other)

    @_intrinsic
    def __lt__(self, rhs: Signed | int | Integer) -> bool:
        assert isinstance(rhs, (Signed, int, Integer))

        if isinstance(rhs, Integer):
            rhs = rhs.get_value()

        if isinstance(rhs, Signed):
            rhs = rhs.to_int()

        return bool(self.to_int() < rhs)

    @_intrinsic
    def __gt__(self, rhs: Signed | int | Integer) -> bool:
        assert isinstance(rhs, (Signed, int, Integer))

        if isinstance(rhs, Integer):
            rhs = rhs.get_value()

        if isinstance(rhs, Signed):
            rhs = rhs.to_int()

        return bool(self.to_int() > rhs)

    @_intrinsic
    def __le__(self, rhs: Signed | int | Integer) -> bool:
        assert isinstance(rhs, (Signed, int, Integer))

        if isinstance(rhs, Integer):
            rhs = rhs.get_value()

        if isinstance(rhs, Signed):
            rhs = rhs.to_int()

        return bool(self.to_int() <= rhs)

    @_intrinsic
    def __ge__(self, rhs: Signed | int | Integer) -> bool:
        assert isinstance(rhs, (Signed, int, Integer))

        if isinstance(rhs, Integer):
            rhs = rhs.get_value()

        if isinstance(rhs, Signed):
            rhs = rhs.to_int()

        return bool(self.to_int() >= rhs)

    @_intrinsic
    def __repr__(self):
        return f"Signed[{self.width-1}:0]({self._bit_str()})"

    @_intrinsic
    def __str__(self):
        return f"{self.to_int()}s"
