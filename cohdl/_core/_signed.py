from __future__ import annotations

from ._bit_vector import BitVector, BitOrder
from ._integer import Integer
from ._boolean import Null, Full

from ._intrinsic import _intrinsic
from cohdl.utility import Span


class Signed(BitVector):
    _is_signed = True
    _SubTypes = {}

    @staticmethod
    @_intrinsic
    def _int_to_binary(width: int, number: int) -> str:
        return "".join([str(int(bool(number & 2**i))) for i in range(width)])[::-1]

    @staticmethod
    @_intrinsic
    def from_int(value: int | Integer):
        if isinstance(value, Integer):
            value = value.get_value()

        if value >= 0 or value.bit_count() != 1:
            width = value.bit_length() + 1
        else:
            width = value.bit_length()

        return Signed[width](value)

    @_intrinsic
    def __init__(
        self,
        val: None | BitVector | str | int = None,
    ):
        if isinstance(val, Integer):
            val = int(val)
        elif isinstance(val, Signed):
            assert (
                val.width <= self.width
            ), f"cannot initialize {type(self)} with wider type {type(val)}"

            val = val.to_int()
        elif isinstance(val, BitVector) and hasattr(val, "_is_unsigned"):
            assert (
                val.width < self.width
            ), f"cannot initialize {type(self)} from {type(val)}"
            val = val.to_int()

        if isinstance(val, int):
            min = -(2 ** (self.width - 1))
            max = 2 ** (self.width - 1)
            assert (
                min <= val < max
            ), f"value {val} outside representable range ({min}-{max-1})"
            val = Signed._int_to_binary(self.width, val)

        super().__init__(val)

    @_intrinsic
    def pow_2(self, exp: int) -> Signed:
        if exp == 0:
            return Signed(self.width, self, self._order)

        if exp > 0:
            return (self.as_bitvector() @ BitVector.zeros(exp)).as_signed()

        if exp >= self.width:
            return Signed(1, 0)

        return self.msb(self.width - exp).as_signed()

    @classmethod
    @_intrinsic
    def min_int(cls) -> int:
        return -(2 ** (cls.width - 1))

    @classmethod
    @_intrinsic
    def max_int(cls) -> int:
        return 2 ** (cls.width - 1) - 1

    @classmethod
    @_intrinsic
    def min(cls) -> Signed:
        return cls(cls.min_int())

    @classmethod
    @_intrinsic
    def max(cls) -> Signed:
        return cls(cls.max_int())

    @_intrinsic
    def _assign(self, other) -> None:
        if isinstance(other, Integer):
            other = int(other)

        if isinstance(other, int):
            assert (
                self.min() <= other <= self.max()
            ), f"assigned value ({other}) outside representable range ({self.min()}-{self.max()})"

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
            assert (
                self.width >= other.width
            ), "assigned value is wider than the target type"
            self._assign(other.to_int())
        elif isinstance(other, BitVector) and hasattr(other, "_is_unsigned"):
            assert (
                self.width > other.width
            ), "assigned unsigned value has equal or larger width than the signed target type"
            self._assign(other.to_int())
        elif isinstance(other, (BitVector, str)) or other is Null or other is Full:
            super()._assign(other)
        else:
            raise AssertionError("invalid source type for assignment to signed value")

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
            rhs = Signed.from_int(rhs)

            if target_width is None:
                # adding integer, that cannot be represented
                # without explicit specification of target_width
                # is probably an error
                assert (
                    rhs.width <= self.width
                ), "added integer is not in the representable target range"
                target_width = self.width
        else:
            if not isinstance(rhs, Signed):
                return NotImplemented

            assert self.order == rhs.order, "bitorder missmatch"

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
    def sub(self, rhs: Signed | int | Integer) -> Signed:
        target_width = None
        if isinstance(rhs, (int, Integer)):
            rhs = Integer.decay(rhs)
            target_width = self.width

        rhs = -rhs
        return self.add(rhs, target_width)

    @_intrinsic
    def __add__(self, rhs: Signed | int | Integer) -> Signed:
        if not isinstance(rhs, (Signed, int, Integer)):
            return NotImplemented

        return self.add(rhs)

    @_intrinsic
    def __radd__(self, lhs: int | Integer) -> Signed:
        if isinstance(lhs, Integer):
            lhs = lhs.get_value()

        return self.add(lhs)

    @_intrinsic
    def __sub__(self, rhs: Signed | int | Integer) -> Signed:
        if not isinstance(rhs, (Signed, int, Integer)):
            return NotImplemented

        return self.sub(rhs)

    @_intrinsic
    def __rsub__(self, lhs: int | Integer) -> Signed:
        if isinstance(lhs, Integer):
            lhs = lhs.get_value()

        return lhs + -self

    @_intrinsic
    def __mul__(self, rhs: Signed) -> Signed:
        if isinstance(rhs, Signed):
            result_width = self.width + rhs.width
            lhs = self.to_int()
            rhs = rhs.to_int()

        elif isinstance(rhs, (int, Integer)):
            result_width = 2 * self.width
            lhs = self.to_int()
            rhs = int(rhs)
        else:
            return NotImplemented

        return Signed[result_width](lhs * rhs)

    @_intrinsic
    def __rmul__(self, lhs: Signed) -> Signed:
        if isinstance(lhs, Signed):
            result_width = self.width + lhs.width
            lhs = lhs.to_int()
            rhs = self.to_int()

        elif isinstance(lhs, (int, Integer)):
            result_width = 2 * self.width
            lhs = int(lhs)
            rhs = self.to_int()
        else:
            return NotImplemented

        return Signed[result_width](lhs * rhs)

    @_intrinsic
    def __floordiv__(self, rhs) -> Signed:
        raise AssertionError(
            f"CoHDL does not support floordiv (the '//' operator) for signed operations. Use cohdl.op.truncdiv instead."
        )

    @_intrinsic
    def __rfloordiv__(self, lhs) -> Signed:
        raise AssertionError(
            f"CoHDL does not support floordiv (the '//' operator) for signed operations. Use cohdl.op.truncdiv instead."
        )

    @_intrinsic
    def _cohdl_truncdiv_(self, rhs: Signed) -> Signed:
        if isinstance(rhs, Signed):
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
            return Signed[result_width]()
        return Signed[result_width](int(lhs / rhs))

    @_intrinsic
    def _cohdl_rtruncdiv_(self, lhs: Signed) -> Signed:
        if isinstance(lhs, Signed):
            result_width = lhs.width
            lhs = lhs.to_int()
            rhs = self.to_int()
        elif isinstance(lhs, (int, Integer)):
            result_width = self.width
            lhs = int(lhs)
            rhs = self.to_int()
        else:
            return NotImplemented

        if rhs == 0:
            return Signed[result_width]()
        return Signed[result_width](int(lhs / rhs))

    @_intrinsic
    def __mod__(self, rhs: Signed) -> Signed:

        if isinstance(rhs, Signed):
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
            return Signed[result_width]()
        return Signed[result_width](lhs % rhs)

    @_intrinsic
    def __rmod__(self, lhs: Signed) -> Signed:

        if isinstance(lhs, Signed):
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
            return Signed[result_width]()
        return Signed[result_width](lhs % rhs)

    @_intrinsic
    def _cohdl_rem_(self, rhs: Signed) -> Signed:

        if isinstance(rhs, Signed):
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
            return Signed[result_width]()

        return Signed[result_width](lhs - rhs * int(lhs / rhs))

    @_intrinsic
    def _cohdl_rrem_(self, lhs: Signed) -> Signed:

        if isinstance(lhs, Signed):
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
            return Signed[result_width]()

        return Signed[result_width](lhs - rhs * int(lhs / rhs))

    @_intrinsic
    def __lshift__(self, rhs) -> Signed:
        try:
            rhs = int(rhs)
        except TypeError:
            return NotImplemented

        width = self.width
        val = (self.to_int() << rhs) & ((1 << width) - 1)

        if val & (1 << (width - 1)):
            val = val - (1 << (width))

        return Signed[self.width](val)

    @_intrinsic
    def __rshift__(self, rhs) -> Signed:
        try:
            rhs = int(rhs)
        except TypeError:
            return NotImplemented

        val = self.to_int() >> rhs
        return Signed[self.width](val)

    @_intrinsic
    def __abs__(self) -> Signed:
        if self >= 0:
            return Signed[self.width](self.to_int())
        else:
            return -self

    @_intrinsic
    def __neg__(self) -> Signed:
        if self._width == 1:
            return self.copy()
        return ~self + 1

    @_intrinsic
    def __eq__(self, other: Signed | int | Integer) -> bool:
        if other is Null or other is Full:
            other = type(self)(other)

        if not isinstance(other, (Signed, int, Integer)):
            return NotImplemented

        if isinstance(other, Integer):
            other = other.get_value()

        if isinstance(other, int):
            return bool(other == self.to_int())

        return bool(other.to_int() == self.to_int())

    @_intrinsic
    def __ne__(self, other: Signed | int | Integer) -> bool:
        if other is Null or other is Full:
            other = type(self)(other)

        if not isinstance(other, (Signed, int, Integer)):
            return NotImplemented

        if isinstance(other, Integer):
            other = other.get_value()

        if isinstance(other, int):
            return bool(other != self.to_int())

        return bool(other.to_int() != self.to_int())

    @_intrinsic
    def __lt__(self, rhs: Signed | int | Integer) -> bool:
        if rhs is Null or rhs is Full:
            rhs = type(self)(rhs)

        if not isinstance(rhs, (Signed, int, Integer)):
            return NotImplemented

        if isinstance(rhs, Integer):
            rhs = rhs.get_value()

        if isinstance(rhs, Signed):
            rhs = rhs.to_int()

        return bool(self.to_int() < rhs)

    @_intrinsic
    def __gt__(self, rhs: Signed | int | Integer) -> bool:
        if rhs is Null or rhs is Full:
            rhs = type(self)(rhs)

        if not isinstance(rhs, (Signed, int, Integer)):
            return NotImplemented

        if isinstance(rhs, Integer):
            rhs = rhs.get_value()

        if isinstance(rhs, Signed):
            rhs = rhs.to_int()

        return bool(self.to_int() > rhs)

    @_intrinsic
    def __le__(self, rhs: Signed | int | Integer) -> bool:
        if rhs is Null or rhs is Full:
            rhs = type(self)(rhs)

        if not isinstance(rhs, (Signed, int, Integer)):
            return NotImplemented

        if isinstance(rhs, Integer):
            rhs = rhs.get_value()

        if isinstance(rhs, Signed):
            rhs = rhs.to_int()

        return bool(self.to_int() <= rhs)

    @_intrinsic
    def __ge__(self, rhs: Signed | int | Integer) -> bool:
        if rhs is Null or rhs is Full:
            rhs = type(self)(rhs)

        if not isinstance(rhs, (Signed, int, Integer)):
            return NotImplemented

        if isinstance(rhs, Integer):
            rhs = rhs.get_value()

        if isinstance(rhs, Signed):
            rhs = rhs.to_int()

        return bool(self.to_int() >= rhs)

    @_intrinsic
    def resize(self, target_width: int | None = None, *, zeros: int = 0):
        if target_width is None:
            target_width = self.width + zeros

        assert (
            self.width + zeros <= target_width
        ), f"width of zero extended value ({self.width}+{zeros}) exceeds target width ({target_width})"
        val = self.to_int() * 2**zeros
        return Signed[target_width](val)

    @_intrinsic
    def __hash__(self) -> int:
        # redefine has method because it is implicitly deleted
        # when __eq__ is defined
        return super().__hash__()

    @_intrinsic
    def __repr__(self):
        return f"Signed[{self.width-1}:0]({self._bit_str()})"

    @_intrinsic
    def __str__(self):
        return f"{self.to_int()}s"
