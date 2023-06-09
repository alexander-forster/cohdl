from __future__ import annotations
from abc import abstractmethod

from typing import Type, TypeVar, NoReturn, overload

import cohdl
from cohdl import Signal, Variable, Bit, BitVector, Unsigned, Signed

T = TypeVar("T")
Self = TypeVar("Self")

class AssignableType:
    @abstractmethod
    def _assign_(self, source, mode: cohdl.AssignMode) -> None: ...
    def _init_qualified_(cls: Type[T], Qualifier, *args, **kwargs) -> T: ...
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

x = make_qualified(Bit, Signal)
