from __future__ import annotations

from ._bit_vector import BitVector, BitOrder
from ._bit import Bit

from ._intrinsic import _intrinsic
from ._integer import Integer

from ._boolean import Null

from cohdl.utility import Span


class Unsigned(BitVector):
    _SubTypes = {}

    @staticmethod
    @_intrinsic
    def upto(max_value: int):
        width = max_value.bit_length()
        return Unsigned[width]

    @staticmethod
    def _uint_to_binary(width: int, number: int) -> str:
        return "".join([str(int(bool(number & 2**i))) for i in range(width)][::-1])

    @staticmethod
    @_intrinsic
    def from_int(
        value: int | Integer,
        max: int | None = None,
        order: BitOrder = BitOrder.DOWNTO,
    ):
        if isinstance(value, Integer):
            value = int(value)

        if max is None:
            max = value

        assert 0 <= value <= max

        width = len(bin(max)) - 2

        return Unsigned[width](value)

    @staticmethod
    def from_str(default: str, order: BitOrder = BitOrder.DOWNTO) -> Unsigned:
        return Unsigned(len(default), default, order)

    @_intrinsic
    def __init__(
        self,
        val: None | BitVector | str | int = None,
    ):
        if isinstance(val, Integer):
            val = int(val)

        if isinstance(val, int):
            assert 0 <= val < 2**self.width
            val = Unsigned._uint_to_binary(self.width, val)

        super().__init__(val)

    def min(self) -> int:
        # only implemented for symmetry with Signed
        return 0

    def max(self) -> int:
        return 2**self.width - 1

    def _assign(self, other):
        import cohdl

        assert not isinstance(
            other, cohdl.Signed
        ), "Signed value cannot be assigned to Unsigned without explicit cast"

        if isinstance(other, Integer):
            other = int(other)

        if isinstance(other, int):
            assert 0 <= other <= self.max()

            binary = Span([*bin(other)[2:]][::-1])

            self._value.apply_zip(
                lambda bit, char: bit._assign(char), binary.iter_extend("0")
            )
        elif isinstance(other, Unsigned):
            assert other.width <= self.width

            self._value.apply_zip(
                lambda bit, other_bit: bit._assign(other_bit),
                other._value.iter_extend(Bit(0)),
            )

        elif (
            isinstance(other, (BitVector, str))
            or other is cohdl.Null
            or other is cohdl.Full
        ):
            super()._assign(other)
        else:
            raise AssertionError()

    def __index__(self):
        return self.to_int()

    @_intrinsic
    def to_int(self) -> int:
        result = 0

        for shift, bit in enumerate(self._value):
            if bit:
                result |= 1 << shift

        return result

    @_intrinsic
    def add(self, rhs: Unsigned | int | Integer, target_width=None) -> Unsigned:
        if isinstance(rhs, (int, Integer)):
            rhs = rhs % 2**self.width
            rhs = Unsigned.from_int(rhs, order=self._order)

            if target_width is None:
                # adding integer, that cannot be represented
                # without explicit specification of target_width
                # is probably an error
                assert rhs.width <= self.width
                target_width = self.width
        else:
            assert self.order == rhs.order
            assert isinstance(rhs, Unsigned)

            if target_width is None:
                target_width = max(self.width, rhs.width)

        target = Unsigned[target_width](Null)

        carry = False

        null_bit = Bit(0)

        for a, b, t in zip(
            self._value.iter_extend(null_bit),
            rhs._value.iter_extend(null_bit),
            target._value,
        ):
            a = bool(a)
            b = bool(b)

            t._assign((a + b + carry) & 1)
            carry = (a + b + carry) > 1

        return target

    @_intrinsic
    def sub(self, rhs: Unsigned | int | Integer, target_width=None) -> Unsigned:
        if isinstance(rhs, Integer):
            rhs = rhs.get_value()

        if isinstance(rhs, int):
            rhs = -(rhs % 2**self.width)

            """assert 0 <= rhs < 2**self.width

            if rhs <= 0:
                rhs = Unsigned.from_int(abs(rhs), order=self._order)
            else:
                rhs = ~Unsigned[self.width](rhs - 1)

            if target_width is None:
                # subtracting integer, that cannot be represented
                # without explicit specification of target_width
                # is probably an error
                assert rhs.width <= self.width"""
        else:
            rhs = -rhs

        return self.add(rhs, target_width)

    @_intrinsic
    def __add__(self, rhs: Unsigned | int | Integer) -> Unsigned:
        return self.add(rhs)

    @_intrinsic
    def __radd__(self, lhs: int | Integer) -> Unsigned:
        return self.add(lhs)

    @_intrinsic
    def __sub__(self, rhs: Unsigned | int | Integer) -> Unsigned:
        return self.sub(rhs)

    @_intrinsic
    def __rsub__(self, lhs: int | Integer) -> Unsigned:
        return lhs + -self

    @_intrinsic
    def __mul__(self, rhs: Unsigned | int | Integer) -> Unsigned:
        result_width = self.width

        if isinstance(rhs, Unsigned):
            result_width = self.width + rhs.width
            rhs = rhs.to_int()
        elif isinstance(rhs, Integer):
            rhs = rhs.get_value()

        lhs = self.to_int()

        return Unsigned[result_width](lhs * rhs)

    @_intrinsic
    def __floordiv__(self, rhs: Unsigned | int | Integer) -> Unsigned:
        result_width = self.width

        if isinstance(rhs, Unsigned):
            rhs = rhs.to_int()
        elif isinstance(rhs, Integer):
            rhs = rhs.get_value()

        lhs = self.to_int()

        if rhs == 0:
            return Unsigned[result_width]()
        return Unsigned[result_width](lhs // rhs)

    @_intrinsic
    def __mod__(self, rhs: Unsigned | int | Integer) -> Unsigned:
        result_width = self.width

        if isinstance(rhs, Unsigned):
            rhs = rhs.to_int()
        elif isinstance(rhs, Integer):
            rhs = rhs.get_value()

        lhs = self.to_int()

        if rhs == 0:
            return Unsigned[result_width]()
        return Unsigned[result_width](lhs % rhs)

    @_intrinsic
    def __lshift__(self, rhs: Unsigned | int | Integer) -> Unsigned:
        i = self.to_int()
        s = int(rhs)
        val = (self.to_int() << int(rhs)) & ((1 << self.width) - 1)
        return Unsigned[self.width](val)

    @_intrinsic
    def __rshift__(self, rhs: Unsigned | int | Integer) -> Unsigned:
        val = self.to_int() >> int(rhs)
        return Unsigned[self.width](val)

    @_intrinsic
    def __neg__(self) -> Unsigned:
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
    def __lt__(self, rhs: Unsigned | int | Integer) -> bool:
        assert isinstance(rhs, (Unsigned, int, Integer))
        if isinstance(rhs, Unsigned):
            rhs = rhs.to_int()

        if isinstance(rhs, Integer):
            rhs = rhs.get_value()

        return bool(self.to_int() < rhs)

    @_intrinsic
    def __gt__(self, rhs: Unsigned | int | Integer) -> bool:
        assert isinstance(rhs, (Unsigned, int, Integer))
        if isinstance(rhs, Unsigned):
            rhs = rhs.to_int()

        if isinstance(rhs, Integer):
            rhs = rhs.get_value()

        return bool(self.to_int() > rhs)

    @_intrinsic
    def __le__(self, rhs: Unsigned | int | Integer) -> bool:
        assert isinstance(rhs, (Unsigned, int, Integer))
        if isinstance(rhs, Unsigned):
            rhs = rhs.to_int()

        if isinstance(rhs, Integer):
            rhs = rhs.get_value()

        return bool(self.to_int() <= rhs)

    @_intrinsic
    def __ge__(self, rhs: Unsigned | int | Integer) -> bool:
        assert isinstance(rhs, (Unsigned, int, Integer))
        if isinstance(rhs, Unsigned):
            rhs = rhs.to_int()

        if isinstance(rhs, Integer):
            rhs = rhs.get_value()

        return bool(self.to_int() >= rhs)

    @_intrinsic
    def resize(self, target_width: int | None, *, zeros: int = 0):
        if target_width is None:
            target_width = self.width + zeros

        assert self.width + zeros <= target_width
        val = self.to_int() * 2**zeros
        return Unsigned[target_width](val)

    @_intrinsic
    def __repr__(self):
        return f"Unsigned[{self.width-1}:0]({self._bit_str()})"

    @_intrinsic
    def __str__(self):
        return f"{self.to_int()}u"
