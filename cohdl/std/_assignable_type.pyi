from __future__ import annotations
from abc import abstractmethod

from typing import Type, TypeVar, NoReturn, overload

import cohdl
from cohdl import Signal, Variable, Bit, BitVector, Unsigned, Signed

T = TypeVar("T")
U = TypeVar("U")
Self = TypeVar("Self")

class AssignableType:
    @abstractmethod
    def _assign_(self, source, mode: cohdl.AssignMode) -> None: ...
    def _init_qualified_(cls: Type[T], Qualifier, *args, **kwargs) -> T: ...
    @classmethod
    def _make_qualified_(cls: Type[T], Qualifier, *args, **kwargs) -> T: ...
    @classmethod
    def signal(cls: Type[T], *args, **kwargs) -> T: ...
    @classmethod
    def variable(cl: Type[T], *args, **kwargs) -> T: ...
    def __ilshift__(self: Self, source) -> Self: ...
    def __imatmul__(self: Self, source) -> Self: ...
    def __ixor__(self: Self, source) -> Self: ...
    @property
    def next(self) -> NoReturn: ...
    @next.setter
    def next(self, value): ...
    @property
    def push(self) -> NoReturn: ...
    @push.setter
    def push(self, value): ...
    @property
    def value(self) -> NoReturn: ...
    @value.setter
    def value(self, value): ...

def make_qualified(Type: type, Qualifier: Signal | Variable, *args, **kwargs) -> T: ...
def make_signal(Type, *args, **kwargs):
    return make_qualified(Type, cohdl.Signal, *args, **kwargs)

def make_variable(Type, *args, **kwargs):
    return make_qualified(Type, cohdl.Variable, *args, **kwargs)

class _Make:
    def __getitem__(self, Qualifier) -> _Make: ...
    def __call__(self, Type, *args, **kwargs): ...

make = _Make()
"""
Helper object, that allows us to construct type qualified objects
of both builtin and custom types.
Custom types are expected to provide a classmethod `_make_qualified_`
that takes a TypeQualifier as its first argument and returns
a new object (See std.AssignableType).

>>> # Signal[Bit]()
>>> make[Signal](Bit)
>>> 
>>> # Variable[BitVector[4]]("1011")
>>> make[Variable](BitVector[4], "1011")
>>>
>>> # MyType._make_qualified_(Signal, arg1, arg2=arg2)
>>> make[Signal](MyType, arg1, arg2=arg2)
"""

make_nonlocal = _Make()
"""
Special version of `std.make` that constructs a new
type qualified object as if it were defined outside the evaluated context.
This can be useful to circumvent the special default-value-semantics
of locally constructed Signals/Variables.

>>> a = Signal[Bit](True)
>>> 
>>> @std.sequential
>>> def process():
>>>     b = make_nonlocal[Signal](Bit, True)
>>>     c = Signal[Bit](True)
>>>     # both a and b are bit signals with a default value of '1'
>>>     # c has no default value but is *immediately* assigned 'True'
>>>     # when it is constructed
"""
