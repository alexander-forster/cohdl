from __future__ import annotations
from ._assignable_type import AssignableType
from cohdl._core import BitVector

import typing

class Field:
    @typing.overload
    def __class_getitem__(cls, offset: int) -> Field.Bit: ...
    @typing.overload
    def __class_getitem__(cls, s: slice) -> Field.BitVector: ...

    class Bit:
        offset: int

        def __class_getitem__(cls, offset: int) -> Field.Bit: ...

    class BitVector:
        start: int
        stop: int

        def __class_getitem__(cls, s: slice) -> Field.BitVector: ...

    class Unsigned: ...
    class Signed: ...

def bitfield(cls):
    class BitField(cls, AssignableType):
        pass
    return cls

def make_bitfield(source, **fields):
    @bitfield
    class _BitField:
        __annotations__ = fields
    return _BitField(source)

def underlying_value(source) -> BitVector:
    """
    return the underlying value (the value passed in the constructor)
    of an instance of a  bitfield class
    """
