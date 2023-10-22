from __future__ import annotations
from typing import Any

import cohdl
from cohdl._core._intrinsic import _intrinsic


class _MetaAssignableType(type):
    @cohdl.consteval
    def __str__(self):
        if hasattr(self, "_class_str_"):
            return self._class_str_()
        return _MetaAssignableType.__repr__(self)

    @cohdl.consteval
    def __repr__(self):
        if hasattr(self, "_class_repr_"):
            return self._class_repr_()
        return self.__name__


class AssignableType(metaclass=_MetaAssignableType):
    def _assign_(self, source, mode: cohdl.AssignMode):
        raise AssertionError("_assign_ must be overwritten")

    # TODO: deprecate _init_qualified_, use _make_qualified_ instead
    @classmethod
    def _init_qualified_(cls, Qualifier, *args, **kwargs):
        return cls(
            *[Qualifier(arg) for arg in args],
            **{name: Qualifier(kwarg) for name, kwarg in kwargs.items()},
        )

    @classmethod
    def _make_qualified_(cls, Qualifier, *args, **kwargs):
        return cls._init_qualified_(Qualifier, *args, **kwargs)

    @classmethod
    def signal(cls, *args, **kwargs):
        return cls._init_qualified_(cohdl.Signal, *args, **kwargs)

    @classmethod
    def variable(cls, *args, **kwargs):
        return cls._init_qualified_(cohdl.Variable, *args, **kwargs)

    def __ilshift__(self, source):
        self._assign_(source, cohdl.AssignMode.NEXT)
        return self

    def __imatmul__(self, source):
        self._assign_(source, cohdl.AssignMode.VALUE)
        return self

    def __ixor__(self, source):
        self._assign_(source, cohdl.AssignMode.PUSH)
        return self

    @property
    def next(self):
        raise AssertionError("next only supported in store context")

    @next.setter
    def next(self, value):
        self <<= value

    @property
    def push(self):
        raise AssertionError("push only supported in store context")

    @push.setter
    def push(self, value):
        self ^= value

    @property
    def value(self):
        raise AssertionError("value only supported in store context")

    @value.setter
    def value(self, value):
        self @= value


def make_qualified(Type, Qualifier, *args, **kwargs):
    if cohdl.is_primitive_type(Type):
        return Qualifier[Type](*args, **kwargs)
    else:
        return Type._make_qualified_(Qualifier, *args, **kwargs)


class _Make:
    def __init__(self, qualifier=None):
        self._qualifier = qualifier

    def __call__(self, Type, *args: Any, **kwargs: Any) -> Any:
        return make_qualified(Type, self._qualifier, *args, **kwargs)

    def __getitem__(self, Qualifier):
        assert self._qualifier is None
        return type(self)(Qualifier)


class _MakeNonlocal(_Make):
    @_intrinsic
    def __call__(self, Type, *args: Any, **kwargs: Any) -> Any:
        print(f"MAKE NONLOCAL {1+3}")
        return super().__call__(Type, *args, **kwargs)


make = _Make()

make_nonlocal = _MakeNonlocal()


def make_signal(Type, *args, **kwargs):
    return make[cohdl.Signal](Type, *args, **kwargs)


def make_variable(Type, *args, **kwargs):
    return make[cohdl.Variable](Type, *args, **kwargs)
