from __future__ import annotations
from ._assignable_type import AssignableType
from cohdl._core import BitVector

from cohdl import Bit, BitVector, Unsigned, Signed
from typing import overload, TypeVar

T = TypeVar("T")

#
#
#

class FieldBit:
    def __new__(cls, source: BitVector) -> Bit: ...

class FieldBitVector:
    def __new__(cls, source: BitVector) -> BitVector: ...

    BitVector: type[FieldBitVector]
    Signed: type[_FieldSigned]
    Unsigned: type[_FieldUnsigned]

class _FieldSigned(FieldBitVector):
    def __new__(cls, source: BitVector) -> Signed: ...

class _FieldUnsigned(FieldBitVector):
    def __new__(cls, source: BitVector) -> Unsigned: ...

class _MetaField(type):
    @overload
    def __getitem__(cls, arg: int) -> type[FieldBit]: ...
    @overload
    def __getitem__(cls, arg: slice) -> type[FieldBitVector]: ...
    @overload
    def __getitem__(
        cls, arg: tuple[slice, type[BitVector]]
    ) -> type[FieldBitVector]: ...
    @overload
    def __getitem__(cls, arg: tuple[slice, type[Signed]]) -> type[_FieldSigned]: ...
    @overload
    def __getitem__(cls, arg: tuple[slice, type[Unsigned]]) -> type[_FieldUnsigned]: ...

class Field(metaclass=_MetaField):
    pass

#
#
#

class _MetaBitField(type):
    def __getitem__(cls, width: int) -> type[_BitFieldInst]: ...

class _MetaBitFieldInst(type):
    @overload
    def __getitem__(cls: type[T], offset: int) -> type[T]: ...
    @overload
    def __getitem__(cls: type[T], slice: slice) -> type[T]: ...

class _BitFieldInst(BitField, metaclass=_MetaBitFieldInst):
    pass

class BitField(AssignableType, metaclass=_MetaBitField):
    _width_: int
    _offset_: int = 0
    Field: type[Field]
