from __future__ import annotations
from ._assignable_type import AssignableType

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
