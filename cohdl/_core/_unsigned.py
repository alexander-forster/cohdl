from __future__ import annotations

from ._bit_vector import BitVector, BitOrder
from ._bit import Bit

from ._intrinsic import _intrinsic
from ._integer import Integer

from ._boolean import Null, Full

from cohdl.utility import Span


class Unsigned(BitVector):
    _is_unsigned = True
    _SubTypes = {}

    @staticmethod
    @_intrinsic
    def upto(max_value: int):
        assert max_value >= 0, "max_value of unsigned cannot be negative"

        if max_value == 0:
            max_value = 1

        width = max_value.bit_length()
        return Unsigned[width]

    @staticmethod
    def _uint_to_binary(width: int, number: int) -> str:
        return "".join([str(int(bool(number & 2**i))) for i in range(width)][::-1])

    @staticmethod
    @_intrinsic
    def from_int(value: int | Integer):
        if isinstance(value, Integer):
            value = int(value)

        assert isinstance(value, int), "expected int or Integer"

        return Unsigned.upto(value)(value)

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

        elif isinstance(val, Unsigned):
            assert (
                val.width <= self.width
            ), f"cannot initialize {type(self)} with wider type {type(val)}"

            val = val.to_int()
        elif isinstance(val, BitVector) and hasattr(val, "_is_signed"):
            raise AssertionError(
                f"cannot initialize unsigned type {type(self)} from signed {type(val)}"
            )

        if isinstance(val, int):
            assert (
                0 <= val < 2**self.width
            ), f"value {val} outside allowed range ({0}-{2**self.width-1})"
            val = Unsigned._uint_to_binary(self.width, val)

        super().__init__(val)

    @classmethod
    @_intrinsic
    def min_int(cls) -> int:
        # only implemented for symmetry with Signed
        return 0

    @classmethod
    @_intrinsic
    def max_int(cls) -> int:
        return 2**cls.width - 1

    @classmethod
    @_intrinsic
    def min(cls) -> Unsigned:
        # only implemented for symmetry with Signed
        return cls(cls.min_int())

    @classmethod
    @_intrinsic
    def max(cls) -> Unsigned:
        return cls(cls.max_int())

    def _assign(self, other):
        if isinstance(other, Integer):
            other = int(other)

        if isinstance(other, int):
            assert 0 <= other <= self.max()

            binary = Span([*bin(other)[2:]][::-1])

            self._value.apply_zip(
                lambda bit, char: bit._assign(char), binary.iter_extend("0")
            )
        elif isinstance(other, Unsigned):
            assert (
                other.width <= self.width
            ), f"target width {self.width} is less than source width {other.width}"

            self._value.apply_zip(
                lambda bit, other_bit: bit._assign(other_bit),
                other._value.iter_extend(Bit(0)),
            )
        elif isinstance(other, BitVector) and hasattr(other, "_is_signed"):
            raise AssertionError(
                "Signed value cannot be assigned to Unsigned without explicit cast"
            )
        elif isinstance(other, (BitVector, str)) or other is Null or other is Full:
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
            rhs = Unsigned.from_int(rhs)

            if target_width is None:
                # adding integer, that cannot be represented
                # without explicit specification of target_width
                # is probably an error
                assert (
                    rhs.width <= self.width
                ), "added integer is not in the representable target range"
                target_width = self.width
        else:
            if not isinstance(rhs, Unsigned):
                return NotImplemented

            assert self.order == rhs.order, "bitorder missmatch"

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
    def __mul__(self, rhs: Unsigned) -> Unsigned:
        if isinstance(rhs, Unsigned):
            result_width = self.width + rhs.width
            lhs = self.to_int()
            rhs = rhs.to_int()
        elif isinstance(rhs, (int, Integer)):
            result_width = 2 * self.width
            lhs = self.to_int()
            rhs = int(rhs)
        else:
            return NotImplemented

        return Unsigned[result_width](lhs * rhs)

    @_intrinsic
    def __rmul__(self, lhs: int) -> Unsigned:
        if isinstance(lhs, Unsigned):
            result_width = self.width + lhs.width
            lhs = lhs.to_int()
            rhs = self.to_int()
        elif isinstance(lhs, (int, Integer)):
            result_width = 2 * self.width
            rhs = self.to_int()
            lhs = int(rhs)
        else:
            return NotImplemented

        return Unsigned[result_width](lhs * rhs)

    @_intrinsic
    def __floordiv__(self, rhs: Unsigned) -> Unsigned:
        if isinstance(rhs, (int, Integer)) or (
            isinstance(rhs, BitVector) and hasattr(rhs, "_is_signed")
        ):
            raise AssertionError(
                f"CoHDL does not support floordiv (the '//' operator) for signed operations. Use cohdl.op.truncdiv instead."
            )

        return self._cohdl_truncdiv_(rhs)

    @_intrinsic
    def __rfloordiv__(self, lhs) -> Unsigned:
        if isinstance(lhs, (int, Integer)) or (
            isinstance(lhs, BitVector) and hasattr(lhs, "_is_signed")
        ):
            raise AssertionError(
                f"CoHDL does not support floordiv (the '//' operator) for signed operations. Use cohdl.op.truncdiv instead."
            )

        return self._cohdl_rtruncdiv_(lhs)

    @_intrinsic
    def _cohdl_truncdiv_(self, rhs: Unsigned) -> Unsigned:

        if isinstance(rhs, Unsigned):
            result_width = self.width
            lhs = self.to_int()
            rhs = rhs.to_int()
        elif isinstance(rhs, (int, Integer)):
            result_width = self.width
            lhs = self.to_int()
            rhs = int(rhs)
        else:
            return NotImplemented

        if rhs == 0:
            return Unsigned[result_width]()
        return Unsigned[result_width](lhs // rhs)

    @_intrinsic
    def _cohdl_rtruncdiv_(self, lhs: int) -> Unsigned:

        if isinstance(lhs, Unsigned):
            result_width = lhs.width
            lhs = lhs.to_int()
            rhs = self.to_int()
        elif isinstance(lhs, (int, Integer)):
            result_width = self.width
            rhs = self.to_int()
            lhs = int(lhs)
        else:
            return NotImplemented

        if rhs == 0:
            return Unsigned[result_width]()
        return Unsigned[result_width](lhs // rhs)

    @_intrinsic
    def __mod__(self, rhs: Unsigned | int | Integer) -> Unsigned:

        if isinstance(rhs, Unsigned):
            result_width = rhs.width
            lhs = self.to_int()
            rhs = rhs.to_int()
        elif isinstance(rhs, (int, Integer)):
            result_width = self.width
            lhs = self.to_int()
            rhs = int(rhs)
        else:
            return NotImplemented

        if rhs == 0:
            return Unsigned[result_width]()
        return Unsigned[result_width](lhs % rhs)

    @_intrinsic
    def __rmod__(self, lhs: int | Integer) -> Unsigned:

        if isinstance(lhs, Unsigned):
            result_width = self.width
            lhs = lhs.to_int()
            rhs = self.to_int()
        elif isinstance(lhs, (int, Integer)):
            result_width = self.width
            lhs = int(lhs)
            rhs = self.to_int()
        else:
            return NotImplemented

        if rhs == 0:
            return Unsigned[result_width]()
        return Unsigned[result_width](lhs % rhs)

    @_intrinsic
    def _cohdl_rem_(self, rhs: Unsigned | int | Integer) -> Unsigned:
        if isinstance(rhs, Unsigned):
            result_width = rhs.width
            rhs = rhs.to_int()
            lhs = self.to_int()
        elif isinstance(rhs, (int, Integer)):
            result_width = self.width
            lhs = self.to_int()
            rhs = int(rhs)
        else:
            return NotImplemented

        if rhs == 0:
            return Unsigned[result_width]()

        return Unsigned[result_width](lhs - rhs * int(lhs / rhs))

    @_intrinsic
    def _cohdl_rrem_(self, lhs: int | Integer) -> Unsigned:
        if isinstance(lhs, (int, Integer)):
            result_width = self.width
            lhs = int(lhs)
            rhs = self.to_int()
        else:
            return NotImplemented

        if rhs == 0:
            return Unsigned[result_width]()

        return Unsigned[result_width](lhs - rhs * int(lhs / rhs))

    @_intrinsic
    def __lshift__(self, rhs: Unsigned | int | Integer) -> Unsigned:
        try:
            rhs = int(rhs)
        except TypeError:
            return NotImplemented

        val = (self.to_int() << rhs) & ((1 << self.width) - 1)
        return Unsigned[self.width](val)

    @_intrinsic
    def __rshift__(self, rhs: Unsigned | int | Integer) -> Unsigned:
        try:
            rhs = int(rhs)
        except TypeError:
            return NotImplemented

        val = self.to_int() >> rhs
        return Unsigned[self.width](val)

    @_intrinsic
    def __neg__(self) -> Unsigned:
        return ~self + 1

    @_intrinsic
    def __eq__(self, other: Unsigned | int | Integer) -> bool:
        if other is Null or other is Full:
            other = type(self)(other)

        if not isinstance(other, (Unsigned, int, Integer)):
            return NotImplemented

        if isinstance(other, Integer):
            other = other.get_value()

        if isinstance(other, int):
            return bool(other == self.to_int())

        return bool(other.to_int() == self.to_int())

    @_intrinsic
    def __ne__(self, other: Unsigned | int | Integer) -> bool:
        if other is Null or other is Full:
            other = type(self)(other)

        if not isinstance(other, (Unsigned, int, Integer)):
            return NotImplemented

        if isinstance(other, Integer):
            other = other.get_value()

        if isinstance(other, int):
            return bool(other != self.to_int())

        return bool(other.to_int() != self.to_int())

    @_intrinsic
    def __lt__(self, rhs: Unsigned | int | Integer) -> bool:
        if rhs is Null or rhs is Full:
            rhs = type(self)(rhs)

        if not isinstance(rhs, (Unsigned, int, Integer)):
            return NotImplemented

        if isinstance(rhs, Unsigned):
            rhs = rhs.to_int()

        if isinstance(rhs, Integer):
            rhs = rhs.get_value()

        return bool(self.to_int() < rhs)

    @_intrinsic
    def __gt__(self, rhs: Unsigned | int | Integer) -> bool:
        if rhs is Null or rhs is Full:
            rhs = type(self)(rhs)

        if not isinstance(rhs, (Unsigned, int, Integer)):
            return NotImplemented

        if isinstance(rhs, Unsigned):
            rhs = rhs.to_int()

        if isinstance(rhs, Integer):
            rhs = rhs.get_value()

        return bool(self.to_int() > rhs)

    @_intrinsic
    def __le__(self, rhs: Unsigned | int | Integer) -> bool:
        if rhs is Null or rhs is Full:
            rhs = type(self)(rhs)

        if not isinstance(rhs, (Unsigned, int, Integer)):
            return NotImplemented

        if isinstance(rhs, Unsigned):
            rhs = rhs.to_int()

        if isinstance(rhs, Integer):
            rhs = rhs.get_value()

        return bool(self.to_int() <= rhs)

    @_intrinsic
    def __ge__(self, rhs: Unsigned | int | Integer) -> bool:
        if rhs is Null or rhs is Full:
            rhs = type(self)(rhs)

        if not isinstance(rhs, (Unsigned, int, Integer)):
            return NotImplemented

        if isinstance(rhs, Unsigned):
            rhs = rhs.to_int()

        if isinstance(rhs, Integer):
            rhs = rhs.get_value()

        return bool(self.to_int() >= rhs)

    @_intrinsic
    def resize(self, target_width: int | None = None, *, zeros: int = 0):
        if target_width is None:
            target_width = self.width + zeros

        assert (
            self.width + zeros <= target_width
        ), f"width of zero extended value ({self.width}+{zeros}) exceeds target width ({target_width})"
        val = self.to_int() * 2**zeros
        return Unsigned[target_width](val)

    @_intrinsic
    def __hash__(self) -> int:
        # redefine has method because it is implicitly deleted
        # when __eq__ is defined
        return super().__hash__()

    @_intrinsic
    def __repr__(self):
        return f"Unsigned[{self.width-1}:0]({self._bit_str()})"

    @_intrinsic
    def __str__(self):
        return f"{self.to_int()}u"
