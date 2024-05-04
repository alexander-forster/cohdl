from __future__ import annotations

from typing import TypeVar, Generic, Literal, get_type_hints
import enum

from cohdl import (
    Null,
    Full,
    Signal,
    Variable,
    BitVector,
    Unsigned,
    Signed,
    Bit,
    Temporary,
    expr_fn,
    always,
)
from cohdl import std
from cohdl._core import AssignMode, Array, true
from cohdl._core._intrinsic import _intrinsic
from cohdl.utility import TextBlock

from .._context import SequentialContext, concurrent
from ..enum import Enum as StdEnum
from .._core_utility import to_bits, NoresetSignal, zeros, ones, concat, base_type
from ..utility import is_pow_two, int_log_2


class Access(enum.Enum):
    na = enum.auto()
    r = enum.auto()
    w = enum.auto()
    w1 = enum.auto()
    rw = enum.auto()
    rw1 = enum.auto()


class HwAccess(enum.Enum):
    na = enum.auto()
    r = enum.auto()
    w = enum.auto()
    rw = enum.auto()


def _expand_lists(inp):
    if isinstance(inp, list):
        result = []

        for elem in inp:
            if isinstance(elem, list):
                result.extend(_expand_lists(elem))
            else:
                result.append(elem)

        return result

    return [inp]


class _None: ...


class _Infinite:
    # The word_count argument is optional for the root AddrMap.
    # When it is not specified an instance of _Infinite is used
    # to pass all bound checks.

    def __add__(self, other):
        return self

    def __radd__(self, other):
        return self

    def __mul__(self, other):
        return self

    def __gt__(self, other):
        return True

    def __ge__(self, other):
        return True

    def __lt__(self, other):
        return False


class GenericArg:
    offset: int = None
    end: int | None = None
    array_step: int | None = None

    def __init__(self, arg):
        self.array_type = None

        if isinstance(arg, tuple):
            array_type, arg = arg
            assert issubclass(array_type, RegisterTools.RegisterObject)
            self.array_type = array_type

        if isinstance(arg, int):
            self.offset = arg
            self.end = None
            self.array_step = None
        elif isinstance(arg, slice):
            assert isinstance(arg.start, int)
            self.offset = arg.start
            self.end = arg.stop
            self.array_step = arg.step

    def __hash__(self) -> int:
        return hash((self.array_type, self.offset, self.end, self.array_step))

    def __eq__(self, other: GenericArg):
        return (
            self.array_type is other.array_type
            and self.offset == other.offset
            and self.end == other.end
            and self.array_step == other.array_step
        )

    def __str__(self):
        return f"{self.offset}"


def _config_wrapper(self, *args, **kwargs):
    assert not hasattr(self, "_cohdlstd_objconfigured")
    result = self._cohdlstd_wrappedconfig(*args, **kwargs)
    setattr(self, "_cohdlstd_objconfigured", True)
    return result


class _RegisterToolsArg:
    word_width: int
    unit_width: int
    word_stride: int

    Field: type[std.bitfield.Field]

    def __init__(self, arg):
        if not isinstance(arg, tuple):
            word_width = arg
            unit_width = 8
        else:
            word_width, unit_width = arg

        assert isinstance(word_width, int)
        assert isinstance(unit_width, int)
        assert (
            word_width % unit_width == 0
        ), "word with must be a multiple of the unit width"

        self.word_width = word_width
        self.unit_width = unit_width
        self.word_stride = word_width // unit_width

    def __hash__(self) -> int:
        return hash((self.word_width, self.unit_width))

    def __eq__(self, other: _RegisterToolsArg) -> bool:
        return (
            self.word_width == other.word_width and self.unit_width == other.unit_width
        )


class RegisterTools(std.Template[_RegisterToolsArg]):
    _word_width_: _RegisterToolsArg.word_width
    _addr_unit_width_: _RegisterToolsArg.unit_width
    _word_stride_: _RegisterToolsArg.word_stride

    @classmethod
    def _as_word_addr_(cls, unit_addr: Unsigned):
        assert is_pow_two(cls._word_stride_)
        drop_bits = int_log_2(cls._word_stride_)
        return unit_addr.msb(rest=drop_bits).copy().unsigned

    @classmethod
    def _as_unit_addr_(cls, word_addr: Unsigned):
        assert is_pow_two(cls._word_stride_)
        add_bits = int_log_2(cls._word_stride_)
        return (word_addr @ zeros(add_bits)).unsigned

    @classmethod
    def _template_specialize_(cls):
        for name in dir(cls):
            subtype = getattr(cls, name)

            if not isinstance(subtype, type):
                continue

            if issubclass(subtype, AddrMap):
                continue

            if issubclass(subtype, (RegFile, AddrRange)):
                setattr(
                    cls,
                    name,
                    type(
                        subtype.__name__,
                        (subtype,),
                        {"_register_tools_": cls},
                        word_count=_None,
                    ),
                )
            elif issubclass(subtype, RegisterObject):
                setattr(
                    cls,
                    name,
                    type(
                        subtype.__name__,
                        (subtype,),
                        {"_register_tools_": cls},
                    ),
                )

        cls.AddrMap = type("AddrMap", (AddrMap, cls.RegFile[0]), {})


class RegisterObject(std.Template[GenericArg]):
    # _register_tools_: type[RegisterTools] = None
    _generic_arg_: GenericArg
    _global_offset_: int
    _parent_offset_: GenericArg.offset

    _readable_: bool = True
    _writable_: bool = True

    _cohdlstd_objhasconfig: bool = False

    @_intrinsic
    def _global_word_offset_(self):
        offset, stride = self._global_offset_, self._register_tools_._word_stride_
        assert (
            offset % stride == 0
        ), f"RegisterObject of type {self} is not word aligned"
        return offset // stride

    @classmethod
    def _template_specialize_(cls):
        assert (
            cls._parent_offset_ % cls._register_tools_._word_stride_ == 0
        ), "all RegisterObjects must be word aligned"

    def __init__(self, parent: RegFile, name: str, _cohdlstd_initguard=None):
        self._name_ = name
        self._global_offset_ = parent._global_offset_ + type(self)._parent_offset_

        assert (
            self._global_offset_ % self._register_tools_._word_stride_ == 0
        ), "all RegisterObjects must be word aligned"

    def _impl_print(self) -> TextBlock:
        import inspect

        doc = inspect.getdoc(type(self))

        return TextBlock(
            [] if doc is None else [doc],
            title=f"{self._name_} @ 0x{self._global_offset_:08x}[{self._word_count_}]",
        )

    def _print_(self, *args, **kwargs):
        print(self._impl_print().dump(), *args, **kwargs)

    def _impl_flatten(self, include_devices) -> list[RegisterObject] | RegisterObject:
        return self

    def _flatten_(self, include_devices=False) -> list[RegisterObject]:
        object_list: list[RegisterObject] = _expand_lists(
            self._impl_flatten(include_devices=include_devices)
        )

        assert all(isinstance(obj, RegisterObject) for obj in object_list)

        reg_tools = self._register_tools_

        assert all(obj._register_tools_ is reg_tools for obj in object_list)

        object_list = sorted(object_list, key=lambda obj: obj._global_word_offset_())

        if not include_devices:
            for current, next in zip(object_list, object_list[1:]):
                assert current._global_word_offset_() < next._global_word_offset_()
                assert (
                    current._global_word_offset_() + current._word_count_
                    <= next._global_word_offset_()
                )

        return object_list

    @classmethod
    @_intrinsic
    def _unit_count_(cls):
        return cls._word_count_ * cls._register_tools_._word_stride_

    @classmethod
    @_intrinsic
    def _word_width_(cls):
        return cls._register_tools_._word_width_

    def _contains_addr_(self, addr: Unsigned):
        global_offset = self._global_offset_
        unit_count = self._unit_count_()

        if std.is_pow_two(unit_count) and global_offset % unit_count == 0:
            return addr.msb(rest=std.int_log_2(unit_count)).unsigned == (
                global_offset // unit_count
            )
        else:
            return global_offset <= addr < (global_offset + unit_count)

    def _basic_read_(self, addr, meta):
        return Null

    def _basic_write_(self, addr, data, mask, meta):
        return None

    def _info_(self):
        pass

    def __init_subclass__(cls, readonly=False, writeonly=False):
        if readonly:
            cls._writable_ = False
        if writeonly:
            cls._readable_ = False

        if "_config_" in cls.__dict__:
            cls._cohdlstd_wrappedconfig = cls.__dict__["_config_"]
            cls._config_ = _config_wrapper

        assert (
            cls._writable_ or cls._readable_
        ), "readonly and writeonly cannot be set at the same time"

    def __str__(self):
        return f"{self._name_} : 0x{self._global_offset_:08x} : {type(self).__name__}"


class RegFile(RegisterObject):
    # _member_types_: dict
    _metadata_ = {}

    def __init__(
        self,
        parent: RegFile | None,
        name: str,
        args=None,
        kwargs=None,
        _cohdlstd_initguard=None,
    ):
        if isinstance(self, AddrMap):
            assert (
                parent is None
            ), "AddrMap may only be used as the root instance (use RegFile for nested register collections)"
        else:
            assert (
                parent is not None
            ), "RegFile cannot be used as the root instance (use AddrMap instead)"
            assert (
                args is None and kwargs is None
            ), "RegFile takes no positional or keyword arguments"

        self._name_ = name

        if parent is None:
            self._global_offset_ = 0
        else:
            self._global_offset_ = parent._global_offset_ + type(self)._parent_offset_

        unit_size = self._unit_count_()

        for name, member_type in type(self)._member_types_.items():

            assert (
                member_type._unit_count_() + member_type._parent_offset_ <= unit_size
            ), f"element '{name}' outside the range of its parent device"

            setattr(
                self,
                name,
                member_type(parent=self, name=name, _cohdlstd_initguard=True),
            )

        if isinstance(self, AddrMap):
            if hasattr(self, "_config_"):
                self._config_(*args, **kwargs)

            for obj in self._flatten_(include_devices=True):
                if (
                    hasattr(obj, "_config_")
                    and not "_cohdlstd_objconfigured" in obj.__dict__
                ):
                    obj._config_()

    def _impl_print(self) -> TextBlock:
        block = super()._impl_print()

        for member in type(self)._member_types_:
            block.add(getattr(self, member)._impl_print())

        return block

    def _impl_flatten(self, include_devices) -> list[RegisterObject]:
        if include_devices:
            result = [self]
        else:
            result = []

        result += [
            getattr(self, name)._impl_flatten(include_devices=include_devices)
            for name in type(self)._member_types_
        ]

        return result

    def _basic_read_(self, addr, meta):
        # RegFile is a collection of RegisterObjects
        # _basic_read_ should be called on them, not on the device
        raise AssertionError("_basic_read_ called on RegisterDevice")

    def _basic_write_(self, addr, data, mask, meta):
        # RegFile is a collection of RegisterObjects
        # _basic_write_ should be called on them, not on the device
        raise AssertionError("_basic_write_ called on RegisterDevice")

    def __init_subclass__(cls, *, word_count=_None, readonly=False, writeonly=False):
        if word_count is _None:
            return

        assert cls.__new__ is RegFile.__new__, "RegFile.__new__ cannot be overloaded"
        assert (
            cls.__init__ is RegFile.__init__ or cls.__init__ is AddrMap.__init__
        ), "RegFile.__init__ cannot be overloaded"
        assert (
            cls._basic_read_ is RegFile._basic_read_
        ), "RegFile._basic_read_ cannot be overloaded"
        assert (
            cls._basic_write_ is RegFile._basic_write_
        ), "RegFile._basic_read_ cannot be overloaded"

        super().__init_subclass__(readonly=readonly, writeonly=writeonly)
        cls._word_count_ = word_count

        if hasattr(cls, "_member_types_"):
            members = {**cls._member_types_}
        else:
            members = {}

        metadata = {}

        for name, member_type in get_type_hints(cls, include_extras=True).items():
            ann_data = None

            if hasattr(member_type, "__metadata__"):
                ann_data = member_type.__metadata__
                member_type = member_type.__origin__

            if issubclass(member_type, RegisterObject):
                assert not name in members, f"{name} shadows existing member"

                if ann_data is not None:
                    metadata[name] = ann_data

                for existing_name, existing_type in members.items():
                    if existing_type._parent_offset_ <= member_type._parent_offset_:
                        assert (
                            existing_type._parent_offset_ + existing_type._unit_count_()
                            <= member_type._parent_offset_
                        ), f"member '{name}' (0x{member_type._parent_offset_}-0x{member_type._parent_offset_+member_type._unit_count_()}) overlaps with member '{existing_name}' (0x{existing_type._parent_offset_}-0x{existing_type._parent_offset_+existing_type._unit_count_()}) of type {cls.__name__}"
                    else:
                        assert (
                            member_type._parent_offset_ + member_type._unit_count_()
                            <= existing_name._parent_offset_
                        ), f"member '{name}' (0x{member_type._parent_offset_}-0x{member_type._parent_offset_+member_type._unit_count_()}) overlaps with member '{existing_name}' (0x{existing_type._parent_offset_}-0x{existing_type._parent_offset_+existing_type._unit_count_()}) of type {cls.__name__}"

                members[name] = member_type

        cls._member_types_ = members
        cls._metadata_ = metadata


class AddrMap(RegFile):
    def __init_subclass__(cls, *, word_count=_None, readonly=False, writeonly=False):
        if word_count is _None:
            word_count = _Infinite()
        super().__init_subclass__(
            word_count=word_count, readonly=readonly, writeonly=writeonly
        )

    def _implement_synthesizable_contexts_(self, ctx: SequentialContext):
        content = self._flatten_(include_devices=True)

        for elem in content:
            if hasattr(elem, "_impl_"):
                elem._impl_(ctx)

            if hasattr(elem, "_impl_sequential_"):
                ctx(elem._impl_sequential_)

            if hasattr(elem, "_impl_concurrent_"):
                concurrent(elem._impl_concurrent_)

    def __init__(self, *args, **kwargs):
        super().__init__(
            parent=None, name=type(self).__name__, args=args, kwargs=kwargs
        )


class GenericRegister(RegisterObject):
    _word_count_ = 1

    async def _basic_read_(self, addr, meta):
        return await std.as_awaitable(self._on_read_)

    async def _basic_write_(self, addr, data, mask, meta):
        return await std.as_awaitable(self._on_write_, data, mask)

    def _on_read_(self):
        return Null

    def _on_write_(self, data, mask):
        pass


class Word(GenericRegister):
    _cohdlstd_vector_type = BitVector

    def _config_(self, default=Null):
        self.raw = Signal[
            self._cohdlstd_vector_type[self._register_tools_._word_width_ - 1 : 0]
        ](default)

    def _on_read_(self):
        return self.raw

    @expr_fn
    def __bool__(self):
        return bool(self.raw)

    def __ilshift__(self, src):
        if isinstance(src, Word):
            self.raw <<= src.raw
        else:
            self.raw <<= src
        return self

    @property
    def next(self):
        raise AssertionError("read from next property not supported")

    def next(self, src):
        self <<= src

    def val(self):
        return self.raw


class UWord(Word):
    _cohdlstd_vector_type = Unsigned


class SWord(Word):
    _cohdlstd_vector_type = Signed


class MemWord(Word):
    def _on_write_(self, data, mask: std.Mask):
        self.raw <<= mask.apply(self.raw, data)


class MemUWord(MemWord):
    _cohdlstd_vector_type = Unsigned


class MemSWord(MemWord):
    _cohdlstd_vector_type = Signed


#
#
#


class _NotifyOnRead: ...


class _NotifyOnWrite: ...


class MetaNotifyBase(type):
    @property
    def Read(cls):
        assert not hasattr(cls, "_cohdlstd_onread")
        return cls[_NotifyOnRead]

    @property
    def Write(cls):
        assert not hasattr(cls, "_cohdlstd_onread")
        return cls[_NotifyOnWrite]


class NotifyArg:
    def __init__(self, arg):
        assert (
            arg is _NotifyOnRead or arg is _NotifyOnWrite
        ), "use NotifyType.Read of NotifyType.Write instead of NotifyType[...]"
        self.arg = arg

    def __hash__(self):
        return hash(self.arg)

    def __eq__(self, other):
        return self.arg is other.arg

    def __str__(self):
        if self.arg is _NotifyOnRead:
            return "on_read"
        return "on_write"


class NotifyBase(std.Template[NotifyArg], metaclass=MetaNotifyBase):
    _cohdlstd_notify_mode: NotifyArg.arg

    def notify(self):
        raise AssertionError("abstract method called")

    def __bool__(self):
        raise AssertionError("abstract method called")


class PushOnNotify(NotifyBase):
    def __init__(self):
        self._bit = Signal[Bit](False)

    def notify(self):
        self._bit ^= True

    @expr_fn
    def __bool__(self):
        return self._bit


class FlagOnNotify(NotifyBase):
    def __init__(self):
        self._flag = std.SyncFlag()

    def notify(self):
        self._flag.set()

    @expr_fn
    def __bool__(self):
        return self._flag.is_set()

    def clear(self):
        self._flag.clear()

    async def __aenter__(self):
        await self._flag.__aenter__()

    async def __aexit__(self, val, type, traceback):
        await self._flag.__aexit__(val, type, traceback)


def _primitive_as_int(input):
    if isinstance(input, Bit):
        return 1 if input else 0

    return input.unsigned.to_int()


class _FieldArg:
    offset: int
    width: int
    is_bit: bool
    default: None
    underlying: None

    def __init__(self, arg):
        self.underlying = None
        self.default = None
        underlying_bit = False
        underlying_width = None

        if isinstance(arg, tuple):
            arg, *rest = arg
            if len(rest) == 0:
                pass
            elif len(rest) == 1:
                if isinstance(rest[0], type):
                    self.underlying = rest[0]
                else:
                    self.default = rest[0]
            elif len(rest) == 2:
                assert isinstance(
                    rest[0], type
                ), f"expected second argument to define the field type but got {rest[0]}"
                self.underlying, self.default = rest
            else:
                raise AssertionError(f"to many arguments for field initializer")

        if self.underlying is not None:
            if self.underlying is Bit or (
                issubclass(self.underlying, StdEnum)
                and self.underlying._underlying_ is Bit
            ):
                underlying_bit = True
                underlying_width = 1
            else:
                underlying_width = std.count_bits(self.underlying)

        if isinstance(arg, int):
            self.offset = arg

            if self.underlying is not None:
                self.width = underlying_width
                self.is_bit = underlying_bit
            else:
                self.width = 1
                self.is_bit = True
        else:
            assert isinstance(
                arg, slice
            ), "first generic argument must be integer or slice"
            assert isinstance(arg.start, int), "slice start must be an integer"
            assert isinstance(arg.stop, int), "slice stop must be an integer"
            assert (
                arg.start >= arg.stop
            ), "slice start must be larger than or equal to slice stop"
            assert arg.step is None, "slice step may not be used"

            self.offset = arg.stop
            self.width = arg.start - arg.stop + 1
            self.is_bit = False

            if self.underlying is not None:
                assert (
                    not underlying_bit
                ), "slice argument cannot be used for a Bit type"
                assert (
                    self.width == underlying_width
                ), f"width of slice argument does not match width of underlying type ({underlying_width})"

        if self.underlying is not None:
            if not issubclass(self.underlying, StdEnum):
                if self.is_bit:
                    assert issubclass(self.underlying, Bit)
                else:
                    assert issubclass(self.underlying, BitVector[self.width])

    def __str__(self) -> str:
        if self.is_bit:
            return str(self.offset)
        else:
            return f"{self.offset+self.width-1}:{self.offset}"

    def __hash__(self) -> int:
        return hash(
            (self.offset, self.width, self.is_bit, self.underlying, type(self.default))
        )

    def is_enum(self):
        return self.underlying is not None and issubclass(self.underlying, StdEnum)

    def get_default_as_int(self):
        if self.underlying is None or self.default is None:
            return None

        default_val = self.underlying(self.default)

        if self.is_enum():
            default_val = default_val.raw

        return _primitive_as_int(default_val)

    def __eq__(self, value: _FieldArg) -> bool:
        return (
            self.offset == value.offset
            and self.width == value.width
            and self.is_bit == value.is_bit
            and self.underlying is value.underlying
            and self.default == value.default
        )


class _FlagArg(_FieldArg):
    def __init__(self, arg):
        super().__init__(arg)
        assert (
            self.is_bit
        ), "FlagField argument must be defined as a single bit (not as a slice)"


class _FieldInfoArg:
    args: tuple

    def __init__(self, arg):
        if isinstance(arg, tuple):
            self.args = arg
        else:
            self.args = (arg,)

    def __hash__(self):
        return hash(self.args)

    def __eq__(self, other: tuple):
        return self.args == other.args


class FieldBase:
    _meta_args_ = ()
    pass


class Field(std.Template[_FieldArg], FieldBase):
    _field_arg: _FieldArg

    @classmethod
    @_intrinsic
    def _cohdlstd_underlying(cls):
        arg = cls._field_arg
        if issubclass(cls, UField):
            vec_type = Unsigned

            if arg.underlying is not None:
                assert issubclass(
                    arg.underlying, Unsigned
                ), "explicit underlying type of UField is not unsigned"
        elif issubclass(cls, SField):
            vec_type = Signed

            if arg.underlying is not None:
                assert issubclass(
                    arg.underlying, Signed
                ), "explicit underlying type of SField is not signed"
        else:
            vec_type = BitVector

        if arg.underlying is None:
            if arg.is_bit:
                return Bit
            else:
                return vec_type[arg.width]

        return arg.underlying

    @classmethod
    def _count_bits_(cls):
        return cls._field_arg.width

    @classmethod
    def _from_bits_(cls, val, qualifier):
        return qualifier[cls](val)

    def _to_bits_(self):
        return to_bits(self._value)

    def __ilshift__(self, other):
        if isinstance(other, Field):
            self._value <<= other._value
        else:
            self._value <<= other
        return self

    def __ixor__(self, other):
        if isinstance(other, Field):
            self._value ^= other._value
        else:
            self._value ^= other
        return self

    def __init__(self, value=None, _qualifier_=Signal, extract=False):
        arg = self._field_arg
        underlying = self._cohdlstd_underlying()

        if extract:
            if underlying is Bit:
                self._value = _qualifier_[Bit](value[arg.offset])
            elif issubclass(underlying, BitVector):
                self._value = _qualifier_[underlying[arg.width]](
                    value[arg.offset + arg.width - 1 : arg.offset]
                )
            else:
                assert issubclass(
                    underlying, StdEnum
                ), "underlying field type must be Bit, BitVector or a std.Enum"

                enum_underlying = underlying._underlying_

                assert issubclass(
                    enum_underlying, (Bit, BitVector)
                ), "the underlying type of an enum field must be a Bit or a BitVector"

                if enum_underlying is Bit:
                    self._value = underlying._unsafe_init_(
                        value[arg.offset], _qualifier_
                    )
                else:
                    self._value = underlying._unsafe_init_(
                        value[arg.offset + arg.width - 1 : arg.offset], _qualifier_
                    )

        else:
            if isinstance(value, Field):
                assert (
                    value._field_arg.width == self._field_arg.width
                ), "width of source field does not match target"
                assert (
                    value._field_arg.is_bit == self._field_arg.is_bit
                ), "only one of source and target field is a Bit type"
                other_value = value._value
            else:
                if value is None:
                    other_value = arg.default
                else:
                    other_value = value

            if underlying is Bit:
                self._value = _qualifier_[Bit](other_value)
            elif issubclass(underlying, BitVector):
                self._value = _qualifier_[underlying[arg.width]](other_value)
            else:
                assert issubclass(
                    underlying, StdEnum
                ), "underlying field type must be Bit, BitVector or a std.Enum"

                self._value = _qualifier_[underlying](other_value)

    def val(self):
        return self._value

    @expr_fn
    def __bool__(self):
        return bool(self._value)


class UField(Field):
    pass


class SField(Field):
    pass


class MemField(Field): ...


class MemUField(UField): ...


class MemSField(SField): ...


class FlagField(std.Template[_FlagArg], FieldBase):
    _field_arg: _FlagArg

    @classmethod
    def _count_bits_(cls):
        return 1

    @classmethod
    def _from_bits_(cls, val: BitVector, qualifier=std.Value):
        assert val.width == 1, "FlagField._from_bits_ expects a single bit BitVector"
        return cls(qualifier[Bit](val[0]))

    def _to_bits_(self):
        if self._has_flag:
            return Temporary[Bit](self._flag.is_set())
        else:
            return Temporary[Bit](self._val)

    def __init__(
        self, inp: Bit | BitVector = None, extract=False, _qualifier_=Signal
    ) -> None:
        super().__init__()

        if inp is None:
            assert extract is False, "inp must be set when extract is requested"
            self._flag = std.SyncFlag()
            self._has_flag = True
        else:
            self._has_flag = False
            if extract:
                self._val = _qualifier_[Bit](inp[self._field_arg.offset])
            else:
                assert std.instance_check(
                    inp, Bit
                ), "inp must be a Bit value unless extract is requested"
                self._val = _qualifier_[Bit](inp)

    def flag(self):
        assert (
            self._has_flag
        ), "this method cannot be used on FlagFields constructed from a received bit"
        return self._flag

    def set(self):
        assert (
            self._has_flag
        ), "this method cannot be used on FlagFields constructed from a received bit"
        self._flag.set()

    def clear(self):
        assert (
            self._has_flag
        ), "this method cannot be used on FlagFields constructed from a received bit"
        self._flag.clear()

    def is_set(self):
        if self._has_flag:
            return self._flag.is_set()
        else:
            return self._val

    def is_clear(self):
        if self._has_flag:
            return self._flag.is_clear()
        else:
            return self._val

    async def __aenter__(self):
        await self._flag.__aenter__()

    async def __aexit__(self, val, type, traceback):
        await self._flag.__aexit__(val, type, traceback)


class Register(GenericRegister):
    # _field_types_: dict[str, std.bitfield.FieldBit | std.bitfield.FieldBitVector]
    _metadata_ = {}

    @classmethod
    def _template_deduce_(cls, *args, **kwargs):
        return cls[0]

    # from RegFile
    def _init_from_device(self, parent, name):
        super().__init__(parent, name)
        self._notifications_ = {}
        for name, notification_type in self._notification_types_.items():
            setattr(self, name, notification_type())
            self._notifications_[name] = getattr(self, name)

        self._init_from_config()

    # from user code
    def _init_from_config(self, **kwargs):
        self._fields_ = {}
        for name, field_type in self._field_types_.items():
            setattr(self, name, field_type())
            self._fields_[name] = getattr(self, name)

        for name, default_val in kwargs:
            member = getattr(self, name)
            assert isinstance(member, (MemField, MemUField, MemSField))
            member._set_default_(default_val)

    # from members
    @_intrinsic
    def _init_from_members(self, members):
        assert len(members) == len(self._field_types_)
        self._fields_ = {}

        for name, value in members.items():
            assert isinstance(value, self._field_types_[name])
            setattr(self, name, value)
            self._fields_[name] = value

    def _init_from_user(self, raw=None, _qualifier_=std.Ref, **kwargs):
        if raw is not None:
            assert len(kwargs) == 0
            self._fields_ = {}

            if std.instance_check(raw, BitVector):
                assert (
                    raw.width == self._register_tools_._word_width_
                ), "raw BitVector width does not match register word width"

                for name, field_type in self._field_types_.items():
                    setattr(
                        self,
                        name,
                        field_type(raw, _qualifier_=_qualifier_, extract=True),
                    )
                    self._fields_[name] = getattr(self, name)
            else:
                # raw is another instance of this class

                for name, field_type in self._field_types_.items():
                    setattr(self, name, _qualifier_[field_type](getattr(raw, name)))
                    self._fields_[name] = getattr(self, name)
        else:
            self._init_from_members(**kwargs)

    def __init__(
        self, *args, _cohdlstd_initguard=False, _cohdlstd_frommembers=False, **kwargs
    ):
        if _cohdlstd_initguard:
            self._init_from_device(*args, **kwargs)
        elif _cohdlstd_frommembers:
            assert len(args) == 1
            assert len(kwargs) == 0
            self._init_from_members(args[0])
        else:
            self._init_from_user(*args, **kwargs)

    def __call__(self, **kwargs):
        all_fields = {**self._fields_, **kwargs}
        tmp_fields = {
            name: std.Value[self._field_types_[name]](field_val)
            for name, field_val in all_fields.items()
        }

        return type(self)(tmp_fields, _cohdlstd_frommembers=True)

    @classmethod
    def _count_bits_(cls):
        return cls._register_tools_._word_width_

    @classmethod
    def _from_bits_(cls, bits: BitVector, qualifier=std.Ref):
        return cls(
            {
                name: qualifier[field_type](bits, extract=True)
                for name, field_type in cls._field_types_.items()
            },
            _cohdlstd_frommembers=True,
        )

    def _to_bits_(self):
        return std.concat(
            *[
                (
                    std.zeros(elem)
                    if isinstance(elem, int)
                    else getattr(self, elem)._to_bits_()
                )
                for elem in self._field_layout_
            ][::-1]
        )

    async def _basic_read_(self, addr, meta):
        for value in self._notifications_.values():
            if value._cohdlstd_notify_mode is _NotifyOnRead:
                value.notify()

        return (await std.as_awaitable(self._on_read_))._to_bits_()

    async def _basic_write_(self, addr, data, mask, meta):
        for value in self._notifications_.values():
            if value._cohdlstd_notify_mode is _NotifyOnWrite:
                value.notify()

        result = await std.as_awaitable(self._on_write_, type(self)._from_bits_(data))

        if result is None:
            # check that self contains no memory
            assert not any(
                [
                    isinstance(field, (MemField, MemUField, MemSField, FlagField))
                    for field in self._fields_.values()
                ]
            )
        else:
            for name, field in self._fields_.items():
                if isinstance(field, (MemField, MemUField, MemSField)):
                    field <<= getattr(result, name)
                elif isinstance(field, FlagField):
                    if getattr(result, name).is_set():
                        field.set()

    def _on_read_(self) -> Register:
        return self

    def _on_write_(self, data):
        return data

    def _assign_(self, source, mode: AssignMode) -> None:
        self._val._assign_(source, mode)

    def __ilshift__(self, source):
        self._val <<= source
        return self

    @property
    def next(self):
        raise AssertionError("next only supported in store context")

    @next.setter
    def next(self, value):
        self._val <<= value

    def _config_(self, **kwargs):
        self._init_from_config(**kwargs)

    def _raw_(self):
        return self._val

    def __init_subclass__(cls, readonly=None, writeonly=None):
        super().__init_subclass__(readonly=readonly, writeonly=writeonly)

        fields: list[tuple[str, type[Field]]] = []
        notifications: list[tuple[str, type[NotifyBase]]] = []
        word_width = cls._register_tools_._word_width_
        metadata = {}

        for name, field_type in get_type_hints(cls, include_extras=True).items():
            if hasattr(field_type, "__metadata__"):
                metadata[name] = field_type.__metadata__
                field_type = field_type.__origin__

            if issubclass(field_type, FieldBase):
                fields.append((name, field_type))

            if issubclass(field_type, NotifyBase):
                notifications.append((name, field_type))

        if len(metadata) != 0:
            cls._metadata_ = metadata

        fields = sorted(fields, key=lambda pair: pair[1]._field_arg.offset)

        # ordered list of field names, padding space is marked
        # by integers giving the number of unused bits
        cls._field_layout_: list[str, int] = []

        offset = 0

        for name, field_type in fields:
            field_offset = field_type._field_arg.offset

            if offset != field_offset:
                assert offset < field_offset, "internal error: offset should be sorted"
                cls._field_layout_.append(field_offset - offset)
            cls._field_layout_.append(name)
            offset = field_offset + field_type._field_arg.width
            assert (
                offset <= word_width
            ), f"register field {name} does not fit in a register of size {word_width}"

        if offset < word_width:
            cls._field_layout_.append(word_width - offset)

        cls._field_types_ = {name: field_type for name, field_type in fields}
        cls._notification_types_ = {
            name: notification_type for name, notification_type in notifications
        }


class Input(GenericRegister, readonly=True):
    def _on_read_(self):
        if self._offset == 0:
            with_offset = self._signal.copy()
        else:
            with_offset = self._signal @ std.zeros(self._offset)

        if self._padding == 0:
            with_padding = with_offset
        else:
            with_padding = std.zeros(self._padding) @ with_offset

        return with_padding

    def _config_(self, signal, /, offset=None, padding=None, lsbs=False, msbs=False):
        assert isinstance(signal, Signal[BitVector])
        width = self._register_tools_._word_width_

        if lsbs:
            assert not msbs, "lsb and msb cannot be set at the same time"
            assert offset is None, "lsb and offset cannot be set at the same time"
            assert padding is None, "lsb and padding cannot be set at the same time"

            offset = 0
            padding = width - signal.width
        elif msbs:
            assert offset is None, "msb and offset cannot be set at the same time"
            assert padding is None, "msb and padding cannot be set at the same time"

            offset = width - signal.width
            padding = 0
        else:
            offset = 0 if offset is None else offset
            padding = 0 if padding is None else padding

        assert (
            signal.width + offset + padding == width
        ), f"resulting input width {signal.width + offset + padding} does not match word width {width}"

        self._signal = signal
        self._width = signal.width
        self._offset = offset
        self._padding = padding


class Output(GenericRegister, writeonly=True):
    def _on_write_(self, data, mask):
        if self._offset == 0:
            with_offset = self._signal
        else:
            with_offset = self._signal @ std.zeros(self._offset)

        if self._padding == 0:
            with_padding = with_offset
        else:
            with_padding = std.zeros(self._padding) @ with_offset

        self._signal <<= (
            mask.apply(with_padding, data)
            .lsb(rest=self._padding)
            .msb(rest=self._offset)
        )

    def _config_(self, signal, offset=None, padding=None, lsbs=False, msbs=False):
        assert isinstance(signal, Signal[BitVector])
        width = self._register_tools_._word_width_

        if lsbs:
            assert not msbs, "lsb and msb cannot be set at the same time"
            assert offset is None, "lsb and offset cannot be set at the same time"
            assert padding is None, "lsb and padding cannot be set at the same time"

            offset = 0
            padding = width - signal.width
        elif msbs:
            assert offset is None, "msb and offset cannot be set at the same time"
            assert padding is None, "msb and padding cannot be set at the same time"

            offset = width - signal.width
            padding = 0
        else:
            offset = 0 if offset is None else offset
            padding = 0 if padding is None else padding

        assert (
            signal.width + offset + padding == width
        ), f"resulting input width {signal.width + offset + padding} does not match word width {width}"

        self._signal = signal
        self._width = signal.width
        self._offset = offset
        self._padding = padding


class Array(RegisterObject):
    _generic_arg_ = None

    def _impl_print(self) -> TextBlock:
        block = super()._impl_print()

        for nr, elem in enumerate(self._elements):
            block.add(elem._impl_print())

        return block

    def _impl_flatten(self, include_devices) -> list[RegisterObject] | RegisterObject:
        if include_devices:
            return [self, *self._elements]
        else:
            return [*self._elements]

    def __init_subclass__(cls, readonly=False, writeonly=False):
        super().__init_subclass__(readonly, writeonly)

        if cls._generic_arg_ is not None:
            assert isinstance(cls._generic_arg_, GenericArg)
            assert (
                cls._generic_arg_.array_step is not None
            ), "array must be defined with a generic step argument"
            cls._word_count_ = (
                cls._generic_arg_.end - cls._generic_arg_.offset
            ) // cls._register_tools_._word_stride_

    def __init__(self, parent: RegFile, name: str, _cohdlstd_initguard=None):
        super().__init__(parent, name)

        arg = type(self)._generic_arg_

        start = arg.offset - self._global_offset_
        stop = arg.end - self._global_offset_
        step = arg.array_step

        elements = []
        prev_offset = self._global_offset_

        for offset in range(start, stop, step):
            # update own offset so child objects are initialized
            # with shifted offset
            # self._global_offset_ = offset
            elements.append(
                arg.array_type[offset](
                    self, "array_elem", _cohdlstd_initguard=_cohdlstd_initguard
                )
            )

        self._elements = elements
        self._global_offset_ = prev_offset

    def __len__(self):
        return len(self._elements)

    def __getitem__(self, index: int):
        return self._elements[index]


class AddrRange(RegisterObject):

    def __init_subclass__(cls, word_count=_None, readonly=False, writeonly=False):
        super().__init_subclass__(readonly, writeonly)

        if hasattr(cls, "_generic_arg_"):
            generic_arg = cls._generic_arg_

            assert isinstance(generic_arg.offset, int)
            assert (
                generic_arg.array_step is None
            ), "AddrRange does not support a generic step parameter"
            assert (
                generic_arg.array_type is None
            ), "AddrRange does not take a generic type parameter"

            word_stride = cls._register_tools_._word_stride_

            if generic_arg.end is not None:
                assert (
                    word_count is _None
                ), "word_count already set using generic argument"
                assert (
                    generic_arg.end - generic_arg.offset
                ) % word_stride == 0, "memory size must be a multiple of the word size"
                word_count = (generic_arg.end - generic_arg.offset) // word_stride

        if word_count is not _None:
            assert not hasattr(
                cls, "_word_count_"
            ), "word_count has already been specified"
            cls._word_count_ = word_count

    async def _basic_read_(self, addr, meta):
        if hasattr(self, "_on_read_"):
            assert not hasattr(
                self, "_on_read_relative_"
            ), "only one of _on_read_ and _on_read_relative_ can be specified"
            return await std.as_awaitable(self._on_read_, addr)
        elif hasattr(self, "_on_read_relative_"):
            return await std.as_awaitable(
                self._on_read_relative_, addr - self._global_offset_
            )

        else:
            return Null

    async def _basic_write_(self, addr, data, mask, meta):
        if hasattr(self, "_on_write_"):
            assert not hasattr(
                self, "_on_write_relative_"
            ), "only one of _on_write_ and _on_write_relative_ can be specified"
            return await std.as_awaitable(self._on_write_, addr, data, mask)
        elif hasattr(self, "_on_write_relative_"):
            return await std.as_awaitable(
                self._on_write_relative_,
                addr - self._global_offset_,
                data,
                mask,
            )


@_intrinsic
def _list_rol(inp: list, roll: int):
    return (inp[roll:] + inp[0:roll])[::-1]


class Memory(AddrRange):
    class MaskMode(enum.Enum):
        IMMEDIATE = enum.auto()
        IGNORE = enum.auto()
        READBACK = enum.auto()
        SPLIT_WORDS = enum.auto()

    def _config_(
        self,
        initial=None,
        noreset=False,
        mask_mode: MaskMode = None,
        allow_unaligned=False,
        inline=False,
    ):
        if mask_mode is None:
            mask_mode = Memory.MaskMode.IMMEDIATE

        if allow_unaligned:
            assert (
                mask_mode is Memory.MaskMode.SPLIT_WORDS
            ), f"unaligned access is currently only supported for MaskMode.SPLIT_WORDS"

        self._register_tools_: RegisterTools
        self._inline = inline

        word_width = type(self)._word_width_()
        word_cnt = type(self)._word_count_

        self._word_stride = self._register_tools_._word_stride_
        self._unit_width = self._register_tools_._addr_unit_width_

        self._mask_mode = mask_mode
        self._allow_unaligned = allow_unaligned

        Qualifier = NoresetSignal if noreset else Signal

        if mask_mode is Memory.MaskMode.SPLIT_WORDS:

            def split_initial(nr):
                if initial is None or initial is Null or initial is Full:
                    return initial
                else:
                    right_bit = self._unit_width * nr
                    left_bit = right_bit + self._unit_width - 1

                    return [
                        BitVector[word_width](elem)[left_bit:right_bit]
                        for elem in initial
                    ]

            self._mem_list = [
                Qualifier[std.Array[BitVector[self._unit_width], word_cnt]](
                    split_initial(nr)
                )
                for nr in range(self._word_stride)
            ]
        else:
            self._mem = Qualifier[std.Array[BitVector[word_width], word_cnt]](initial)

    async def _cohdlstd_impl_read(self, addr):
        waddr = self._register_tools_._as_word_addr_(addr)
        if self._mask_mode is self.MaskMode.SPLIT_WORDS:
            stride_cnt = int_log_2(self._word_stride)
            stride_bits = addr.lsb(stride_cnt).unsigned

            if not self._allow_unaligned:
                assert stride_bits == 0, "stride error"

                return concat(
                    *[
                        self._mem_list[unit_nr][waddr]
                        for unit_nr in range(self._word_stride)
                    ][::-1]
                )
            else:

                rddata = [
                    self._mem_list[off][
                        waddr
                        + (Unsigned[1](0) if stride_bits <= off else Unsigned[1](1))
                    ]
                    for off in range(self._word_stride)
                ]

                result = Variable[BitVector[self._word_width_()]]()

                for off in range(self._word_stride):
                    if stride_bits == off:
                        result @= concat(*_list_rol(rddata, off))

                return result
        else:
            return self._mem[waddr]

    async def _cohdlstd_impl_write(self, addr, data, mask):
        waddr = Variable(self._register_tools_._as_word_addr_(addr))

        if self._mask_mode is self.MaskMode.IGNORE:
            self._mem[waddr] <<= data
        elif self._mask_mode is self.MaskMode.IMMEDIATE:
            self._mem[waddr] <<= mask.apply(self._mem[waddr], data)
        elif self._mask_mode is self.MaskMode.READBACK:
            prev_val = Signal(self._mem[waddr])
            await true
            self._mem[waddr] <<= mask.apply(prev_val, data)
        elif self._mask_mode is self.MaskMode.SPLIT_WORDS:
            unit_mask = mask.as_vector(self._word_width_())

            if not self._allow_unaligned:
                for unit_nr in range(self._word_stride):
                    right_bit = self._unit_width * unit_nr
                    left_bit = right_bit + self._unit_width - 1

                    if unit_mask[unit_nr * self._unit_width]:
                        self._mem_list[unit_nr][waddr] <<= data[left_bit:right_bit]
            else:
                stride_cnt = int_log_2(self._word_stride)
                stride_bits = addr.lsb(stride_cnt).unsigned

                addr_list = [
                    Variable[base_type(waddr)]() for _ in range(self._word_stride)
                ]
                data_list = [
                    Variable[BitVector[self._unit_width]]()
                    for _ in range(self._word_stride)
                ]
                mask_list = [Variable[Bit]() for _ in range(self._word_stride)]

                for unit_nr in range(self._word_stride):
                    val = addr_list[unit_nr]

                    val @= waddr + (
                        Unsigned[1](0) if stride_bits <= unit_nr else Unsigned[1](1)
                    )

                for off in range(self._word_stride):
                    if off == stride_bits:
                        for unit_nr in range(self._word_stride):
                            lsb = self._find_lsb_of_unaligned_split(off, unit_nr)

                            msb = lsb + self._unit_width - 1

                            data_list[unit_nr] @= data[msb:lsb]
                            mask_list[unit_nr] @= unit_mask[lsb]

                for unit_nr in range(self._word_stride):
                    if mask_list[unit_nr]:
                        self._mem_list[unit_nr][addr_list[unit_nr]] <<= data_list[
                            unit_nr
                        ]

    def _impl_(self, ctx: SequentialContext):
        if not self._inline:
            self._rd_enable = Signal[Bit](False)
            self._rd_addr = Signal[Unsigned.upto(self._unit_count_())]()
            self._rd_data = Signal[Unsigned[self._word_width_()]]()

            self._wr_enable = Signal[Bit](False)
            self._wr_addr = Signal[Unsigned.upto(self._unit_count_())]()
            self._wr_data = Signal[Unsigned[self._word_width_()]]()

            if self._mask_mode is not self.MaskMode.IGNORE:
                self._wr_mask = Signal[BitVector[self._word_width_()]]()
            else:
                self._wr_mask = None

            @ctx
            async def impl_read_memory():
                if self._rd_enable:
                    self._rd_data <<= await self._cohdlstd_impl_read(self._rd_addr)

            @ctx
            async def impl_write_memory():
                if self._mask_mode is self.MaskMode.READBACK:
                    while True:
                        if self._wr_enable:
                            await self._cohdlstd_impl_write(
                                self._wr_addr, self._wr_data, std.Mask(self._wr_mask)
                            )
                            continue
                else:
                    if self._wr_enable:
                        await self._cohdlstd_impl_write(
                            self._wr_addr, self._wr_data, std.Mask(self._wr_mask)
                        )

    async def _on_read_relative_(self, addr):
        if self._inline:
            return await self._cohdlstd_impl_read(addr)
        else:
            self._rd_addr <<= addr.lsb(self._rd_addr.width)
            self._rd_enable ^= True
            await true
            await true
            return self._rd_data

    async def _on_write_relative_(self, addr, data, mask):
        if self._inline:
            await self._cohdlstd_impl_write(addr, data, mask)
        else:
            if self._mask_mode is not self.MaskMode.IGNORE:
                self._wr_mask <<= mask.as_vector(self._word_width_())

            self._wr_addr <<= addr.lsb(self._wr_addr.width)
            self._wr_data <<= data
            self._wr_enable ^= True

    @_intrinsic
    def _find_lsb_of_unaligned_split(self, addr_offset, unit_nr):
        word_width = self._word_width_()
        unit_width = self._unit_width

        return (word_width + ((unit_nr - addr_offset) * unit_width)) % word_width


class RoMemory(Memory):
    def __init_subclass__(cls, word_count=_None):
        return super().__init_subclass__(word_count, readonly=True, writeonly=False)

    def _config_(self, initial, mask_mode=None, inline=False):
        return super()._cohdlstd_wrappedconfig(
            initial, noreset=True, mask_mode=mask_mode, inline=inline
        )


RegisterTools.RegisterObject = RegisterObject
RegisterTools.RegFile = RegFile
RegisterTools.AddrMap = AddrMap

RegisterTools.NotifyBase = NotifyBase
RegisterTools.PushOnNotify = PushOnNotify
RegisterTools.FlagOnNotify = FlagOnNotify

RegisterTools.GenericRegister = GenericRegister
RegisterTools.Register = Register

RegisterTools.Word = Word
RegisterTools.UWord = UWord
RegisterTools.SWord = SWord
RegisterTools.MemWord = MemWord
RegisterTools.MemUWord = MemUWord
RegisterTools.MemSWord = MemSWord

RegisterTools.Access = Access
RegisterTools.HwAccess = HwAccess
RegisterTools.Field = Field
RegisterTools.UField = UField
RegisterTools.SField = SField
RegisterTools.MemField = MemField
RegisterTools.MemUField = MemUField
RegisterTools.MemSField = MemSField
RegisterTools.FlagField = FlagField


RegisterTools.Input = Input
RegisterTools.Output = Output
RegisterTools.Array = Array
RegisterTools.AddrRange = AddrRange

RegisterTools.Memory = Memory
RegisterTools.RoMemory = RoMemory

reg32 = RegisterTools[32, 8]
