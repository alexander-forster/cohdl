from __future__ import annotations

import enum

from ._primitive_type import _PrimitiveType
from ._boolean import Null, _NullFullType, _Boolean
from ._intrinsic import _intrinsic


class BitState(enum.Enum):
    LOW = enum.auto()
    HIGH = enum.auto()
    UNINITIALZED = enum.auto()
    UNKNOWN = enum.auto()
    HIGH_IMPEDANCE = enum.auto()
    WEAK = enum.auto()
    WEAK_LOW = enum.auto()
    WEAK_HIGH = enum.auto()
    DONT_CARE = enum.auto()

    @_intrinsic
    def __bool__(self) -> bool:
        return self is BitState.HIGH

    @_intrinsic
    def __invert__(self) -> BitState:
        if self is BitState.LOW:
            return BitState.HIGH
        elif self is BitState.HIGH:
            return BitState.LOW
        else:
            return BitState.UNKNOWN

    @_intrinsic
    def __or__(self, other) -> BitState:
        return BitState.HIGH if BitState.HIGH in (self, other) else BitState.LOW

    @_intrinsic
    def __and__(self, other) -> BitState:
        return BitState.LOW if BitState.LOW in (self, other) else BitState.HIGH

    @_intrinsic
    def __xor__(self, other) -> BitState:
        return BitState.LOW if self == other else BitState.HIGH

    @_intrinsic
    def __str__(self) -> str:
        if self is BitState.LOW:
            return "0"
        elif self is BitState.HIGH:
            return "1"
        elif self is BitState.UNINITIALZED:
            return "U"
        elif self is BitState.UNKNOWN:
            return "X"
        elif self is BitState.HIGH_IMPEDANCE:
            return "Z"
        else:
            return "-"

    @staticmethod
    @_intrinsic
    def from_str(char: str) -> BitState:
        if char == "0":
            return BitState.LOW
        elif char == "1":
            return BitState.HIGH
        elif char == "U":
            return BitState.UNINITIALZED
        elif char == "X":
            return BitState.UNKNOWN
        elif char == "-":
            return BitState.DONT_CARE

        raise AssertionError(f"cannot construct BitState from string '{char}'")

    @staticmethod
    @_intrinsic
    def construct(
        arg: BitState | Bit | str | int | bool | _NullFullType | None,
    ) -> BitState:
        from ._integer import Integer
        from ._boolean import true, false

        if arg is None:
            return BitState.UNINITIALZED

        if isinstance(arg, Integer):
            arg = arg.get_value()

        if arg is true:
            arg = True
        elif arg is false:
            arg = False

        if isinstance(arg, BitState):
            return arg
        elif isinstance(arg, Bit):
            return arg.get()
        elif isinstance(arg, (bool, _Boolean)):
            return BitState.HIGH if arg else BitState.LOW
        elif isinstance(arg, int):
            assert arg == 0 or arg == 1, f"cannot construct BitState from {arg}"
            return BitState.HIGH if arg else BitState.LOW
        elif isinstance(arg, str):
            return BitState.from_str(arg)
        elif isinstance(arg, _NullFullType):
            if arg is Null:
                return BitState.LOW
            return BitState.HIGH

        raise AssertionError(f"cannot construct BitState from object {arg}")


class _MetaBit(type):
    @_intrinsic
    def __str__(cls):
        return "Bit"

    @_intrinsic
    def __repr__(cls):
        return "Bit"


class Bit(_PrimitiveType, metaclass=_MetaBit):
    @_intrinsic
    def __init__(
        self,
        value: (
            Bit | None | BitState | str | int | bool | _NullFullType
        ) = BitState.UNINITIALZED,
    ):
        self._val = BitState.construct(value)

    @_intrinsic
    def _is_uninitialized(self):
        return self._val == BitState.UNINITIALZED

    @_intrinsic
    def copy(self) -> Bit:
        return Bit(self)

    @_intrinsic
    def _assign(self, other: BitState | Bit | str | int | bool | _NullFullType):
        assert other is not None, "cannot assign None to Bit"
        self._val = BitState.construct(other)

    @property
    @_intrinsic
    def type(self):
        return Bit

    @_intrinsic
    def get(self) -> BitState:
        return self._val

    @_intrinsic
    def invert(self) -> Bit:
        return ~self

    @_intrinsic
    def __invert__(self) -> Bit:
        return Bit(~self._val)

    @_intrinsic
    def __inv__(self) -> Bit:
        return Bit(~self._val)

    @_intrinsic
    def __or__(self, other: Bit) -> Bit:
        return Bit(self._val | other._val)

    @_intrinsic
    def __and__(self, other: Bit) -> Bit:
        return Bit(self._val & other._val)

    @_intrinsic
    def __xor__(self, other: Bit) -> Bit:
        return Bit(self._val ^ other._val)

    @_intrinsic
    def __matmul__(self, other):
        from ._bit_vector import BitVector

        if isinstance(other, Bit):
            return BitVector[2](f"{self}{other}")
        elif isinstance(other, BitVector):
            return other.__rmatmul__(self)

        return NotImplemented

    @_intrinsic
    def __bool__(self) -> bool:
        return self._val is BitState.HIGH

    @_intrinsic
    def __eq__(self, other: Bit | BitState) -> bool:
        if isinstance(other, Bit):
            return self._val is other._val
        else:
            return self._val is BitState.construct(other)

    @_intrinsic
    def __ne__(self, other: Bit | BitState) -> bool:
        if isinstance(other, Bit):
            return self._val is not other._val
        else:
            return self._val is not BitState.construct(other)

    @_intrinsic
    def __len__(self):
        return 1

    @_intrinsic
    def __hash__(self):
        return int(self._val is BitState.HIGH)

    @_intrinsic
    def __str__(self) -> str:
        return str(self._val)

    @_intrinsic
    def __repr__(self) -> str:
        return f"Bit({self._val})"
