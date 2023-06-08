from __future__ import annotations
from ._assignable_type import AssignableType

import cohdl
import typing


class Field:
    def __class_getitem__(cls, *args):
        assert len(args) == 1
        arg = args[0]

        if isinstance(arg, int):
            return Field.Bit[arg]
        else:
            assert isinstance(arg, slice)
            assert arg.step is None
            return Field.BitVector[arg.start : arg.stop]

    class Bit:
        offset: int

        def __new__(cls, source):
            return source[cls.offset]

        def __class_getitem__(cls, offset_):
            class Bit(Field.Bit):
                offset = offset_

            return Bit

    class BitVector:
        start: int
        stop: int

        def __new__(cls, source):
            return source[cls.start : cls.stop].bitvector

        def __class_getitem__(cls, arg):
            class BitVector(Field.BitVector):
                start = arg.start
                stop = arg.stop

            class Unsigned(BitVector):
                def __new__(cls, source):
                    return source[cls.start : cls.stop].unsigned

            class Signed(BitVector):
                def __new__(cls, source):
                    return source[cls.start : cls.stop].signed

            BitVector.BitVector = BitVector
            BitVector.Unsigned = Unsigned
            BitVector.Signed = Signed

            return BitVector

    class Unsigned:
        pass

    class Signed:
        pass


class _BitfieldClass(AssignableType):
    ...


def bitfield(cls_=None, *, offset=0):
    def helper(cls):
        assert (
            cls.__init__ is object.__init__ or cls.__init__ is AssignableType.__init__
        )
        assert not hasattr(cls, "_assign_") or cls._assign_ is AssignableType._assign_
        assert (
            not hasattr(cls, "init_from")
            or cls.init_from.__func__ is AssignableType.init_from.__func__
        )

        fixed_width = cls_ if isinstance(cls_, int) else None

        fields = {
            name: value
            for name, value in typing.get_type_hints(cls).items()
            if issubclass(value, (Field.Bit, Field.BitVector, _BitfieldClass))
        }

        subbitfields = {
            name: value
            for name, value in cls.__dict__.items()
            if isinstance(value, type) and issubclass(value, _BitfieldClass)
        }

        class BitfieldClass(_BitfieldClass, cls):
            __name__ = cls.__name__

            def __init__(self, input_vector, *, extract_sub=False):
                offset_ = offset
                if extract_sub:
                    assert fixed_width is not None
                    input_vector = input_vector[offset_ + fixed_width - 1 : offset_]
                    offset_ = 0

                if fixed_width is not None:
                    assert fixed_width == len(input_vector)

                for name, Field in fields.items():
                    setattr(self, name, Field(input_vector.msb(rest=offset_)))

                for name, Sub in subbitfields.items():
                    setattr(self, name, Sub(input_vector, extract_sub=True))

                self._input_vector = input_vector

            def _assign_(self, source, mode: cohdl.AssignMode):
                if isinstance(source, _BitfieldClass):
                    assert isinstance(source, type(self))

                    for name in fields:
                        getattr(self, name)._assign_(getattr(source, name), mode)

                    for name_ in subbitfields:
                        getattr(self, name_)._assign_(getattr(source, name_), mode)
                elif isinstance(source, dict):
                    for name, value in source.items():
                        getattr(self, name)._assign_(value, mode)
                else:
                    self._input_vector._assign_(source, mode)

            @classmethod
            def _init_qualified_(cls, TypeQualifyer, **defaults):
                assert fixed_width is not None

                initial = cohdl.BitVector[fixed_width]()

                if len(defaults) != 0:
                    inital_view = cls(initial)
                    inital_view._assign_(defaults)

                return cls(TypeQualifyer(initial))

        for name, value in fields.items():
            setattr(BitfieldClass, name, value)

        for name, value in subbitfields.items():
            setattr(BitfieldClass, name, value)

        BitfieldClass.__name__ = cls.__name__
        return BitfieldClass

    if cls_ is None or isinstance(cls_, int):
        return helper
    return helper(cls_)


def make_bitfield(source, **fields):
    @bitfield
    class _BitField:
        __annotations__ = fields

    return _BitField(source)


def underlying_value(source):
    return source._input_vector
