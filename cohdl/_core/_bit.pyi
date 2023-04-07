from __future__ import annotations

import enum

from ._primitive_type import _PrimitiveType
from ._boolean import _NullFullType
from ._bit_vector import BitVector

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

    def __bool__(self) -> bool: ...
    def __invert__(self) -> BitState: ...
    def __or__(self, other) -> BitState: ...
    def __and__(self, other) -> BitState: ...
    def __xor__(self, other) -> BitState: ...
    @staticmethod
    def from_str(char: str) -> BitState: ...
    @staticmethod
    def construct(
        arg: BitState | Bit | str | int | bool | _NullFullType | None,
    ) -> BitState: ...

class Bit(_PrimitiveType):
    def __init__(
        self,
        value: Bit
        | None
        | BitState
        | str
        | int
        | bool
        | _NullFullType = BitState.UNINITIALZED,
    ):
        self._val: BitState
    def copy(self) -> Bit: ...
    @property
    def type(self):
        return Bit
    def get(self) -> BitState: ...
    def invert(self) -> Bit: ...
    def __invert__(self) -> Bit: ...
    def __inv__(self) -> Bit: ...
    def __or__(self, other: Bit) -> Bit: ...
    def __and__(self, other: Bit) -> Bit: ...
    def __xor__(self, other: Bit) -> Bit: ...
    def __matmul__(self, other) -> BitVector: ...
    def __bool__(self) -> bool: ...
    def __eq__(self, other: Bit | BitState) -> bool: ...
    def __ne__(self, other: Bit | BitState) -> bool: ...
    def __len__(self) -> int: ...
    def __hash__(self) -> int: ...
