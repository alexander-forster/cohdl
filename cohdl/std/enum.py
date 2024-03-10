from __future__ import annotations

from cohdl._core import BitVector, Unsigned, AssignMode, Signal
from cohdl._core._intrinsic import _intrinsic
from ._template import Template
from ._core_utility import Value, to_bits, from_bits, count_bits
from ._assignable_type import AssignableType

import inspect


class _TemplateArg:
    def __init__(self, arg):
        if isinstance(arg, tuple):
            underlying, owner = arg
        else:
            underlying = arg
            owner = None

        if underlying is not None:
            assert isinstance(underlying, type)

        self.underlying = underlying
        self.owner = owner

    def __hash__(self) -> int:
        return hash((self.underlying, self.owner))

    def __eq__(self, other: _TemplateArg):
        return self.underlying is other.underlying and self.owner is other.owner


class Enum(Template[_TemplateArg], AssignableType):
    _underlying_: _TemplateArg.underlying
    _default_: Enum
    __members__: dict[str, Enum]

    @property
    def raw(self):
        return self._val

    @raw.setter
    def raw(self, value):
        assert (
            value is self._val
        ), "assignment to the raw property only allowed using `<<=`, `^=` or `@=`"
        pass

    @property
    @_intrinsic
    def name(self):
        assert hasattr(
            self, "_name"
        ), "the name property is only defined for the constant enumerators used in the declaration"
        return self._name

    @property
    @_intrinsic
    def info(self):
        assert hasattr(
            self, "_info"
        ), "the info property is only defined for the constant enumerators used in the declaration"
        return self._info

    @classmethod
    @_intrinsic
    def _count_bits_(cls):
        return count_bits(cls._underlying_)

    @classmethod
    def _from_bits_(cls, bits, qualifier=Value):
        return cls(
            from_bits[cls._underlying_](bits, qualifier),
            _qualifier_=qualifier,
            _unsafe_init=True,
        )

    def _to_bits_(self):
        return to_bits(self._val)

    @classmethod
    def _unsafe_init_(cls, value, _qualifier_=Value):
        return cls(value, _qualifier_=_qualifier_, _unsafe_init=True)

    def _assign_(self, source, mode: AssignMode) -> None:
        assert type(self) is type(source)
        self._val._assign_(source._val, mode)

    @classmethod
    def _template_deduce_(cls, *args, **kwargs) -> Template[_TemplateArg]:
        return Enum[None]

    def _init_enumerator(self, val, info: str | None = None):
        self._val = val
        self._info = info

    def _init_normal(self, val=None, _qualifier_=Value, _unsafe_init=False):
        underlying = type(self)._underlying_

        if val is None:
            self._val = _qualifier_[underlying](self._default_._val)
        elif isinstance(val, Enum):
            if type(val) is type(self):
                self._val = _qualifier_[underlying](val._val)
            else:
                assert val._underlying_ is None
                assert _unsafe_init, "invalid argument type"
                self._val = _qualifier_[underlying](val._val)
                self._info = val._info
                self._name = val._name
        else:
            assert _unsafe_init, "invalid argument type"
            self._val = _qualifier_[underlying](val)

    def __init__(self, *args, **kwargs):

        if type(self)._underlying_ is None:
            self._init_enumerator(*args, **kwargs)
        else:
            self._init_normal(*args, **kwargs)

    def __init_subclass__(cls) -> None:
        if not hasattr(cls, "_underlying_"):
            # template not yet specialized
            return

        if "_underlying_" in cls.__dict__:
            # template specialized but not used class has been derived
            return

        enumerators = {}

        for name, value in cls.__dict__.items():
            if name.startswith("__") or inspect.isfunction(value):
                continue

            if isinstance(value, Enum):
                enumerator = value
            else:
                if isinstance(value, tuple):
                    value, info = value
                else:
                    info = None

                enumerator = Enum(value, info)

            enumerator._name = name
            enumerators[name] = cls(enumerator, _unsafe_init=True)

        is_first = True

        for name, enumerator in enumerators.items():
            if is_first:
                is_first = False
                setattr(cls, "_default_", enumerator)
                setattr(cls, "__members__", enumerators)
            setattr(cls, name, enumerator)

    def __eq__(self, other):
        assert type(self) is type(other)
        return self._val == other._val

    def __ne__(self, other):
        assert type(self) is type(other)
        return self._val != other._val

    def __bool__(self):
        return bool(self._val)


class FlagEnum(Enum):
    def __and__(self, other):
        assert type(self) is type(other)
        return type(self)(self._val & other._val, _unsafe_init=True)

    def __or__(self, other):
        assert type(self) is type(other)
        return type(self)(self._val | other._val, _unsafe_init=True)

    def __xor__(self, other):
        assert type(self) is type(other)
        return type(self)(self._val ^ other._val, _unsafe_init=True)
