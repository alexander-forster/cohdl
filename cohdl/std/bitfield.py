from __future__ import annotations
from ._assignable_type import AssignableType
from cohdl._core._intrinsic import _intrinsic

import cohdl
import typing

from ._core_utility import Ref, instance_check, fail
from ._template import Template


class BitArg(int):
    pass


class FieldBit(Template[BitArg]):
    _offset_: BitArg

    @_intrinsic
    def __new__(cls, source: cohdl.BitVector):
        return source[cls._offset_]


class BitVectorArg:
    start: int
    stop: int
    type: type

    @_intrinsic
    def __init__(self, arg: slice) -> None:
        if not isinstance(arg, tuple):
            arg = (arg, cohdl.BitVector)

        span: slice = arg[0]

        assert isinstance(span, slice), "first generic argument must be a slice"
        assert isinstance(span.start, int), "start parameter must be an integer"
        assert isinstance(span.stop, int), "stop parameter must be an integer"
        assert span.step is None, "step parameter not allowed"
        assert arg[1] in (
            cohdl.BitVector,
            cohdl.Signed,
            cohdl.Unsigned,
        ), f"invalid argument type {arg[1]}"

        self.start = span.start
        self.stop = span.stop
        self.type = arg[1]

    @_intrinsic
    def __str__(self) -> str:
        return f"{self.start}:{self.stop},{self.type}"

    def __hash__(self) -> int:
        return hash((self.start, self.stop, self.type))

    def __eq__(self, other: BitVectorArg):
        return (
            self.start == other.start
            and self.stop == other.stop
            and self.type is other.type
        )


class FieldBitVector(Template[BitVectorArg]):
    _start_: BitVectorArg.start
    _stop_: BitVectorArg.stop
    _type_: BitVectorArg.type

    BitVector: FieldBitVector[BitVectorArg.start : BitVectorArg.stop, cohdl.BitVector]
    Signed: FieldBitVector[BitVectorArg.start : BitVectorArg.stop, cohdl.Signed]
    Unsigned: FieldBitVector[BitVectorArg.start : BitVectorArg.stop, cohdl.Unsigned]

    @_intrinsic
    def __new__(cls, source: cohdl.BitVector):
        if cls._type_ is cohdl.BitVector:
            return source[cls._start_ : cls._stop_]
        elif cls._type_ is cohdl.Unsigned:
            return source[cls._start_ : cls._stop_].unsigned
        elif cls._type_ is cohdl.Signed:
            return source[cls._start_ : cls._stop_].signed
        else:
            fail("invalid target type {}", cls._type_)


class Field:
    def __class_getitem__(cls, arg):
        if isinstance(arg, int):
            return FieldBit[arg]
        else:
            return FieldBitVector[arg]


_bitfield_classes: dict[int, type[BitField]] = {}


class BitField(AssignableType):
    @_intrinsic
    def __class_getitem__(cls, arg):
        assert isinstance(arg, int)

        if arg not in _bitfield_classes:
            newtype = type(
                f"BitField[{arg}]",
                (_BitFieldInst,),
                {
                    "_cohdlstd_is_bitfield_base": True,
                    "_width_": arg,
                    "_offset_": None,
                },
            )

            _bitfield_classes[arg] = newtype

        return _bitfield_classes[arg]

    def __init__(self, vec: cohdl.BitVector | None = None, *, _qualifier_=Ref):
        if vec is None:
            self._vec = _qualifier_[cohdl.BitVector[self._width_]]()
        elif vec is cohdl.Null or vec is cohdl.Full:
            self._vec = _qualifier_[cohdl.BitVector[self._width_]](vec)
        elif isinstance(vec, BitField):
            assert isinstance(
                vec, type(self)
            ), "bitfield type of argument does not match target"
            self._vec = _qualifier_(vec._vec)
        else:
            assert (
                vec.width == self._width_
            ), "vector width does not match bitfield width"
            self._vec = _qualifier_(vec)

        for name, Field in self._fields_.items():
            if issubclass(Field, (FieldBit, FieldBitVector)):
                setattr(self, name, Field(self._vec))
            else:
                assert issubclass(
                    Field, BitField
                ), "internal error: member of BitField has unexpected type {}".format(
                    Field
                )
                assert (
                    Field._offset_ is not None
                ), "the offset of sub-BitFields must be specified"

                subvec = self._vec.msb(rest=Field._offset_).lsb(Field._width_)
                setattr(self, name, Field(subvec, _qualifier_=Ref))

    def _assign_(self, source, mode: cohdl.AssignMode):
        if isinstance(source, BitField):
            assert isinstance(source, type(self))
            self._vec._assign_(source._vec, mode)
        elif isinstance(source, dict):
            for name, value in source.items():
                getattr(self, name)._assign_(value, mode)
        else:
            assert instance_check(source, cohdl.BitVector[self._width_])
            self._vec._assign_(source, mode)

    @classmethod
    @_intrinsic
    def _count_bits_(cls):
        return cls._width_

    @classmethod
    def _from_bits_(cls, bitvector: cohdl.BitVector, qualifier):
        return cls(bitvector, _qualifier_=qualifier)

    def _to_bits_(self):
        return cohdl.Temporary(self._vec)

    @_intrinsic
    def __str__(self):
        fields = {name: str(getattr(self, name)) for name in self._fields_}
        return f"{type(self).__name__}({self._vec}, {fields})"


BitField.Field = Field


class BitfieldArgs:
    def __init__(self, arg):
        assert isinstance(arg, int)
        self.offset: int = arg

    @_intrinsic
    def __str__(self) -> str:
        return str(self.offset)

    def __hash__(self) -> int:
        return hash(self.offset)

    def __eq__(self, other: BitfieldArgs) -> bool:
        return self.offset == other.offset


class _BitFieldInst(BitField):
    # _offset_: int
    # _fields_: dict[str, type]

    @_intrinsic
    def __class_getitem__(cls, arg):
        if isinstance(arg, slice):
            assert isinstance(arg.start, int), "slice start must be an integer"
            assert isinstance(arg.stop, int), "slice stop must be an integer"
            assert arg.step is None, "slice step may not be used"
            assert (
                arg.start - arg.stop + 1 == cls._width_
            ), f"slice width ({arg.start}:{arg.stop}=={arg.start - arg.stop + 1}) does not match BitField width {cls._width_}"
            arg = arg.stop

        assert isinstance(arg, int), "expected slice or integer"
        subclasses = cls._cohdlstd_subclasses

        if arg in subclasses:
            return subclasses[arg]

        newtype = type(
            f"{cls.__name__}[{arg}]",
            (subclasses[None],),
            {"_offset_": arg, "_cohdlstd_is_offset_bitfield": False},
        )
        subclasses[arg] = newtype
        return newtype

    @_intrinsic
    def __init_subclass__(cls):
        if "_cohdlstd_is_bitfield_base" in cls.__dict__:
            return

        if hasattr(cls, "_cohdlstd_bitfield_init_done"):
            assert (
                cls._cohdlstd_is_offset_bitfield == False
            ), "BitFields may not be derived"
            cls._cohdlstd_is_offset_bitfield = True
            return

        fields = {}
        for name, value in typing.get_type_hints(cls).items():
            assert issubclass(
                value, (FieldBit, FieldBitVector, _BitFieldInst)
            ), f"invalid BitField element type {value} of element '{name}'"
            fields[name] = value

        cls._fields_ = fields
        setattr(cls, "_cohdlstd_bitfield_init_done", True)
        setattr(cls, "_cohdlstd_subclasses", {None: cls})
