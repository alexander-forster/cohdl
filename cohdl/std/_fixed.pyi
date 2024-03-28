from __future__ import annotations

from cohdl import BitVector, Null, Full

from ._core_utility import Value

from ._assignable_type import AssignableType

import enum

import typing
from typing import Self

T = typing.TypeVar("T")

#
#
#

class FixedRoundStyle(enum.Enum):
    ROUND = enum.auto()
    TRUNCATE = enum.auto()

class FixedOverflowStyle(enum.Enum):
    SATURATE = enum.auto()
    WRAP = enum.auto()

#
#

class _FixedResize(typing.Generic[T]):
    def __call__(
        self,
        round_style: FixedRoundStyle = FixedRoundStyle.TRUNCATE,
        overflow_style: FixedRoundStyle = FixedOverflowStyle.WRAP,
    ) -> T: ...

class _Resize(typing.Generic[T]):
    def __call__(
        self,
        left: int,
        right: int,
        round_style: FixedRoundStyle = FixedRoundStyle.TRUNCATE,
        overflow_style: FixedRoundStyle = FixedOverflowStyle.WRAP,
    ) -> T: ...
    def __getitem__(self, arg: slice) -> _FixedResize[T]: ...

#
#

class SFixed(AssignableType):
    resize: _Resize[SFixed]

    def resize_fn(
        self,
        left: int,
        right: int,
        round_style: FixedRoundStyle = FixedRoundStyle.TRUNCATE,
        overflow_style: FixedRoundStyle = FixedOverflowStyle.WRAP,
    ) -> SFixed: ...
    def __class_getitem__(cls, arg: slice) -> SFixed: ...
    @classmethod
    def _count_bits_(cls) -> int: ...
    @classmethod
    def _from_bits_(cls, bits: BitVector, qualifier=Value) -> Self: ...
    def _to_bits_(self) -> BitVector: ...
    @classmethod
    def min(cls) -> float: ...
    @classmethod
    def max(cls) -> float: ...
    @classmethod
    def right(cls) -> int: ...
    @classmethod
    def left(cls) -> int: ...
    def __init__(
        self, val: int | Null | Full | SFixed = None, *, _qualifier_=Value
    ): ...
    def __eq__(self, other: int | float | SFixed) -> bool: ...
    def __bool__(self) -> bool: ...
    def __abs__(self) -> SFixed: ...
    def __add__(self, other: SFixed) -> SFixed: ...
    def __sub__(self, other: SFixed) -> SFixed: ...
    def __mul__(self, other: SFixed) -> SFixed: ...

#
#

class UFixed(AssignableType):
    resize: _Resize[UFixed]

    def resize_fn(
        self,
        left: int,
        right: int,
        round_style: FixedRoundStyle = FixedRoundStyle.TRUNCATE,
        overflow_style: FixedRoundStyle = FixedOverflowStyle.WRAP,
    ) -> UFixed: ...
    def __class_getitem__(cls, arg: slice) -> UFixed: ...
    @classmethod
    def _count_bits_(cls) -> int: ...
    @classmethod
    def _from_bits_(cls, bits: BitVector, qualifier=Value) -> Self: ...
    def _to_bits_(self) -> BitVector: ...
    @classmethod
    def min(cls) -> int: ...
    @classmethod
    def max(cls) -> float: ...
    @classmethod
    def right(cls) -> int: ...
    @classmethod
    def left(cls) -> int: ...
    def __init__(
        self, val: int | Null | Full | SFixed = None, *, _qualifier_=Value
    ): ...
    def __eq__(self, other: int | float | UFixed) -> bool: ...
    def __bool__(self) -> bool: ...
    def __abs__(self) -> Self: ...
    def __add__(self, other: UFixed) -> UFixed: ...
    def __sub__(self, other: UFixed) -> UFixed: ...
    def __mul__(self, other: UFixed) -> UFixed: ...
