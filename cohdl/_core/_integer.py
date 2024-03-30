from __future__ import annotations
from ._intrinsic import _intrinsic
from ._primitive_type import _PrimitiveType


class Integer(_PrimitiveType):
    @staticmethod
    def decay(value: int | Integer) -> int:
        import cohdl

        if isinstance(value, int):
            assert not isinstance(value, bool)
            pass
        elif isinstance(value, Integer):
            value = value.get_value()
            assert isinstance(value, int)
        elif isinstance(value, (cohdl.Unsigned, cohdl.Signed)):
            value = value.to_int()

        assert isinstance(value, int), f"value is {value}, expected integer"

        return value

    def __init__(
        self,
        val: int | Integer | None = None,
        *,
        min: int | None = None,
        max: int | None = None,
    ):
        import cohdl

        self._min = min
        self._max = max

        if val is cohdl.Null:
            val = 0

        if val is None:
            self._val = 0
        else:
            assert isinstance(val, (int, Integer))
            self._val = int(val) if isinstance(val, int) else val.get_value()

    @property
    def type(self):
        return Integer

    def get_value(self) -> int:
        return self._val

    def copy(self):
        return Integer(self._val, min=self._min, max=self._max)

    def _assign(self, other: int | Integer):
        import cohdl

        if isinstance(other, Integer):
            other = other.get_value()
        elif isinstance(other, (cohdl.Unsigned, cohdl.Signed)):
            other = other.to_int()

        if self._min is not None:
            assert (
                self._min <= other
            ), f"assigned value {other} is smaller than the set minimum {self._min}"
        if self._max is not None:
            assert (
                self._max >= other
            ), f"assigned value {other} is larger than the set maximum {self._max}"

        assert isinstance(other, int), f"expected an integer argument not {other}"
        self._val = other

    def __hash__(self) -> int:
        return self._val

    @_intrinsic
    def __bool__(self) -> bool:
        return self._val != 0

    @_intrinsic
    def __index__(self) -> int:
        assert isinstance(
            self._val, int
        ), f"index expects an integer value not {self._val}"
        return self._val

    @_intrinsic
    def __add__(self, other: int | Integer) -> Integer:
        return Integer(self._val + Integer.decay(other))

    @_intrinsic
    def __radd__(self, other: int) -> Integer:
        return Integer(other + self._val)

    @_intrinsic
    def __sub__(self, other: int | Integer) -> Integer:
        return Integer(self._val - Integer.decay(other))

    @_intrinsic
    def __rsub__(self, other: int) -> Integer:
        return Integer(other - self._val)

    @_intrinsic
    def __and__(self, other: int | Integer) -> Integer:
        return Integer(self._val & Integer.decay(other))

    @_intrinsic
    def __or__(self, other: int | Integer) -> Integer:
        return Integer(self._val | Integer.decay(other))

    @_intrinsic
    def __xor__(self, other: int | Integer) -> Integer:
        return Integer(self._val ^ Integer.decay(other))

    @_intrinsic
    def __rand__(self, other: int) -> Integer:
        return Integer(self._val & other)

    @_intrinsic
    def __ror__(self, other: int) -> Integer:
        return Integer(self._val | other)

    @_intrinsic
    def __rxor__(self, other: int) -> Integer:
        return Integer(self._val ^ other)

    @_intrinsic
    def __floordiv__(self, other: int | Integer) -> Integer:
        return Integer(self._val // Integer.decay(other))

    @_intrinsic
    def __rfloordiv__(self, other: int) -> Integer:
        return Integer(other // self._val)

    @_intrinsic
    def __neg__(self) -> Integer:
        return Integer(-self._val)

    @_intrinsic
    def __pos__(self) -> Integer:
        return Integer(self._val)

    @_intrinsic
    def __eq__(self, other: int | Integer) -> bool:
        return bool(self._val == Integer.decay(other))

    @_intrinsic
    def __ne__(self, other) -> bool:
        return bool(self._val != Integer.decay(other))

    @_intrinsic
    def __gt__(self, other) -> bool:
        other = Integer.decay(other)
        assert self._val is not None, "integer value is not set"

        return bool(self._val > other)

    @_intrinsic
    def __lt__(self, other) -> bool:
        other = Integer.decay(other)
        assert self._val is not None, "integer value is not set"

        return bool(self._val < other)

    @_intrinsic
    def __ge__(self, other) -> bool:
        other = Integer.decay(other)
        assert self._val is not None, "integer value is not set"

        return bool(self._val >= other)

    @_intrinsic
    def __le__(self, other) -> bool:
        other = Integer.decay(other)
        assert self._val is not None, "integer value is not set"

        return bool(self._val <= other)

    @_intrinsic
    def __str__(self):
        return str(self._val)

    @_intrinsic
    def __repr__(self):
        return f"Integer({self._val}, min={self._min}, max={self._max})"
