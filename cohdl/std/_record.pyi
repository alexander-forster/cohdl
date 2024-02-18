from __future__ import annotations

from typing import Self, dataclass_transform

from cohdl._core import BitVector

from ._core_utility import Value
from ._assignable_type import AssignableType
from ._template import Template

@dataclass_transform()
class Record(AssignableType, Template):
    """
    `std.Record` automates the process of creating user defined
    data types, that conform to `std.AssignableType` and the serialization
    primitives `std.to_bits`/`std.from_bits`/`std.count_bits`.

    >>> Example
    >>>
    >>> class MyType(std.Record):
    >>>     a: BitVector[8]
    >>>     b: Bit
    >>>     c: Signed[4]
    >>>
    >>> inst_a = MyType(BitVector[8](Null), )

    """

    @classmethod
    def _count_bits_(cls) -> int: ...
    @classmethod
    def _from_bits_(cls: type[Self], bits, qualifier=Value) -> Self: ...
    def _to_bits_(self) -> BitVector: ...
    def __repr__(self) -> str: ...
    def __str__(self) -> str: ...
    def __eq__(self, other) -> bool: ...
    def __ne__(self, other) -> bool: ...
