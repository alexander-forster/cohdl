from __future__ import annotations

import typing
from typing import TypeVar
from ._primitive_type import _PrimitiveType

T = TypeVar("T")
Self = TypeVar("Self")

class Array(typing.Generic[T], _PrimitiveType):
    _elemtype_: type[T]
    _count_: int

    def __init__(self, val=None): ...
    def __len__(self) -> int: ...
    def __getitem__(self, slice): ...
    def __setitem__(self, slice, arg): ...
    def copy(self: Self) -> Self: ...
    def __hash__(self) -> int: ...
