from __future__ import annotations

from typing import TypeVar, Generic, Literal, get_type_hints
import enum

from cohdl import Null, Signal, BitVector, Unsigned, Signed, Bit, Temporary
from cohdl import std
from cohdl._core import AssignMode
from cohdl._core._intrinsic import _intrinsic
from cohdl.utility import TextBlock

from ._context import SequentialContext, concurrent


class AccessMode(enum.Enum):
    READ_WRITE = enum.auto()
    READ_ONLY = enum.auto()
    WRITE_ONLY = enum.auto()


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


class _32_:
    pass


class _64_:
    pass


class _None: ...


class GenericArg:
    offset: int = None
    end: int = None
    array_step: int = None

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
        assert word_width % unit_width == 0

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
    def _template_specialize_(cls):
        for name in dir(cls):
            subtype = getattr(cls, name)

            if not isinstance(subtype, type):
                continue

            if issubclass(subtype, RootDevice):
                continue

            if issubclass(subtype, (RegisterDevice, AddrRange)):
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

        cls.RootDevice = type("RootDevice", (RootDevice, cls.RegisterDevice[0]), {})


class RegisterObject(std.Template[GenericArg]):
    # _register_tools_: type[RegisterTools] = None
    _generic_arg_: GenericArg
    _global_offset_: int
    _parent_offset_: GenericArg.offset
    _global_word_offset_: int
    # _word_count_: int
    _access_: AccessMode = AccessMode.READ_WRITE
    __metadata__ = ()

    _readable_: bool = True
    _writable_: bool = True

    _cohdlstd_objhasconfig: bool = False

    @classmethod
    def _template_specialize_(cls):
        assert (
            cls._parent_offset_ % cls._register_tools_._word_stride_ == 0
        ), "all RegisterObjects must be word aligned"

    def __init__(self, parent: RegisterDevice, name: str, _cohdlstd_initguard=None):
        self._name_ = name
        self._global_offset_ = parent._global_offset_ + type(self)._parent_offset_

        assert (
            self._global_offset_ % self._register_tools_._word_stride_ == 0
        ), "all RegisterObjects must be word aligned"

        self._global_word_offset_ = (
            self._global_offset_ // self._register_tools_._word_stride_
        )

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

        object_list = sorted(object_list, key=lambda obj: obj._global_word_offset_)

        if not include_devices:
            for current, next in zip(object_list, object_list[1:]):
                assert current._global_word_offset_ < next._global_word_offset_
                assert (
                    current._global_word_offset_ + current._word_count_
                    <= next._global_word_offset_
                )

        return object_list

    @classmethod
    def _unit_count_(cls):
        return cls._word_count_ * cls._register_tools_._word_stride_

    def _word_width_(self):
        return type(self)._register_tools_._word_width_

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


class RegisterDevice(RegisterObject):
    # _member_types_: dict

    def __init__(
        self,
        parent: RegisterDevice | None,
        name: str,
        args=None,
        kwargs=None,
        _cohdlstd_initguard=None,
    ):
        if isinstance(self, RootDevice):
            assert parent is None
        else:
            assert parent is not None
            assert args is None and kwargs is None

        self._name_ = name

        if parent is None:
            self._global_offset_ = 0
            self._global_word_offset_ = 0
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

        if isinstance(self, RootDevice):
            if hasattr(self, "_config_"):
                self._config_(*args, **kwargs)

            for obj in self._flatten_():
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
        # RegisterDevice is a collection of RegisterObjects
        # _basic_read_ should be called on them, not on the device
        raise AssertionError("_basic_read_ called on RegiserDevice")

    def _basic_write_(self, addr, data, mask, meta):
        # RegisterDevice is a collection of RegisterObjects
        # _basic_write_ should be called on them, not on the device
        raise AssertionError("_basic_write_ called on RegiserDevice")

    def __init_subclass__(cls, *, word_count=_None, readonly=False, writeonly=False):
        if word_count is _None:
            return

        assert cls.__new__ is RegisterDevice.__new__
        assert (
            cls.__init__ is RegisterDevice.__init__
            or cls.__init__ is RootDevice.__init__
        )
        assert cls._basic_read_ is RegisterDevice._basic_read_
        assert cls._basic_write_ is RegisterDevice._basic_write_

        super().__init_subclass__(readonly=readonly, writeonly=writeonly)
        cls._word_count_ = word_count

        if hasattr(cls, "_member_types_"):
            members = {**cls._member_types_}
        else:
            members = {}

        for name, member_type in get_type_hints(cls, include_extras=True).items():
            if issubclass(member_type, RegisterObject):
                assert not name in members, f"{name} shadows existing member"

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


class RootDevice(RegisterDevice):
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
        return await std.as_awaitable(self._on_read_(self))

    async def _basic_write_(self, addr, data, mask, meta):
        return await std.as_awaitable(self._on_write_(self, data, mask))

    def _on_read_(self):
        return Null

    def _on_write_(self, data, mask):
        pass


#
#
#


class _FieldArg:
    offset: int
    width: int
    is_bit: bool
    default: None

    def __init__(self, arg):
        if isinstance(arg, tuple):
            arg, self.default = arg
        else:
            self.default = None

        if isinstance(arg, int):
            self.offset = arg
            self.width = 1
            self.is_bit = True
        else:
            assert isinstance(arg, slice)
            assert isinstance(arg.start, int)
            assert isinstance(arg.stop, int)
            assert arg.start >= arg.stop
            assert arg.step is None

            self.offset = arg.stop
            self.width = arg.start - arg.stop + 1
            self.is_bit = False

    def __str__(self) -> str:
        if self.is_bit:
            return str(self.offset)
        else:
            return f"{self.offset+self.width-1}:{self.offset}"

    def __hash__(self) -> int:
        return hash((self.offset, self.width, self.is_bit, type(self.default)))

    def __eq__(self, value: _FieldArg) -> bool:
        return (
            self.offset == value.offset
            and self.width == value.width
            and self.is_bit == value.is_bit
            and self.default == value.default
        )


class _FlagArg(_FieldArg):
    def __init__(self, arg):
        super().__init__(arg)
        assert self.is_bit


class FieldBase:
    pass


class Field(std.Template[_FieldArg], FieldBase):
    _field_arg: _FieldArg
    _vec_type = BitVector

    @classmethod
    def _count_bits_(cls):
        return cls._field_arg.width

    @classmethod
    def _from_bits_(cls, val, qualifier):
        return qualifier[cls](val)

    def _to_bits_(self):
        return Temporary(self._value)

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

        if extract:
            if arg.is_bit:
                self._value = _qualifier_[Bit](value[arg.offset])
            else:
                self._value = _qualifier_[self._vec_type[arg.width]](
                    value[arg.offset + arg.width - 1 : arg.offset]
                )
        else:
            if isinstance(value, Field):
                assert value._field_arg.width == self._field_arg.width
                assert value._field_arg.is_bit == self._field_arg.is_bit
                other_value = value._value
            else:
                if value is None:
                    other_value = arg.default
                else:
                    other_value = value

            if arg.is_bit:
                self._value = _qualifier_[Bit](other_value)
            else:
                self._value = _qualifier_[self._vec_type[arg.width]](other_value)

    def value(self):
        return self._value


class UField(Field):
    _vec_type = Unsigned


class SField(Field):
    _vec_type = Signed


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
        assert val.width == 1
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
            assert extract is False
            self._flag = std.SyncFlag()
            self._has_flag = True
        else:
            self._has_flag = False
            if extract:
                self._val = _qualifier_[Bit](inp[self._field_arg.offset])
            else:
                assert std.instance_check(inp, Bit)
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


class Register(GenericRegister):
    # _field_types_: dict[str, std.bitfield.FieldBit | std.bitfield.FieldBitVector]

    @classmethod
    def _template_deduce_(cls, *args, **kwargs):
        return cls[0]

    # from RegisterDevice
    def _init_from_device(self, parent, name):
        super().__init__(parent, name)
        self._init_from_config()

    # from user code
    def _init_from_config(self, **kwargs):
        self._fields_ = {}
        for name, field_type in self._field_types_.items():
            setattr(self, name, field_type())
            self._fields_[name] = getattr(self, name)

        for name, default_val in kwargs:
            member = getattr(self, name)
            assert isinstance(member, MemField)
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
                assert raw.width == self._register_tools_._word_width_

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
        return (await std.as_awaitable(self._on_read_))._to_bits_()

    async def _basic_write_(self, addr, data, mask, meta):
        result = await std.as_awaitable(self._on_write_, type(self)._from_bits_(data))

        if result is None:
            # assert self contains no memory
            assert not any(
                isinstance(field, (MemField, FlagField))
                for field in result._fields_.values()
            )
        else:
            for name, field in self._fields_.items():
                if isinstance(field, MemField):
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
        word_width = cls._register_tools_._word_width_

        for name, field_type in get_type_hints(cls, include_extras=True).items():
            if issubclass(field_type, FieldBase):
                fields.append((name, field_type))

        fields = sorted(fields, key=lambda pair: pair[1]._field_arg.offset)

        # ordered list of field names, padding space is marked
        # by integers giving the number of unused bits
        cls._field_layout_: list[str, int] = []

        offset = 0

        for name, field_type in fields:
            field_offset = field_type._field_arg.offset

            if offset != field_offset:
                assert offset < field_offset
                cls._field_layout_.append(field_offset - offset)
            cls._field_layout_.append(name)
            offset = field_offset + field_type._field_arg.width
            assert (
                offset <= word_width
            ), f"register field {name} does not fit in a register of size {word_width}"

        if offset < word_width:
            cls._field_layout_.append(word_width - offset)

        cls._field_types_ = {name: field_type for name, field_type in fields}


# class R(Register, readonly=True):
#    pass


# class W(Register, writeonly=True):
#    pass


class Input(GenericRegister, readonly=True):
    def _on_read_(self):
        reg_width = self._register_tools_._word_width_

        if self._width == reg_width:
            return self._signal.copy()
        else:
            return std.zeros(reg_width - self._width) @ self._signal

    def _config_(self, signal):
        assert isinstance(signal, Signal[BitVector])
        assert signal.width <= self._register_tools_._word_width_
        self._signal = signal
        self._width = signal.width


class Output(GenericRegister, writeonly=True):
    def _on_write_(self, data, mask):
        self._signal <<= std.apply_mask(
            self._signal, data.lsb(self._width), mask.lsb(self._width)
        )

    def _config_(self, signal):
        assert isinstance(signal, Signal[BitVector])
        assert signal.width <= self._register_tools_._word_width_
        self._signal = signal
        self._width = signal.width


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
            assert cls._generic_arg_.array_step is not None
            cls._word_count_ = (
                cls._generic_arg_.end
                - cls._generic_arg_.offset // cls._register_tools_._word_stride_
            )

    def __init__(self, parent: RegisterDevice, name: str, _cohdlstd_initguard=None):
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

        if word_count is not _None:
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
            return await std.as_awaitable(self._on_write_relative_, addr, data, mask)


RegisterTools.RegisterObject = RegisterObject
RegisterTools.RegisterDevice = RegisterDevice
RegisterTools.RootDevice = RootDevice

RegisterTools.GenericRegister = GenericRegister
RegisterTools.Register = Register
RegisterTools.RW = Register
# RegisterTools.R = R
# RegisterTools.W = W
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


reg32 = RegisterTools[32, 8]