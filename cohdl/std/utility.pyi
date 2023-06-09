from __future__ import annotations

from typing import TypeVar, Generic

from cohdl._core import Bit, BitVector

def iscouroutinefunction(fn) -> bool: ...
def instance_check(val, type) -> bool:
    return isinstance(val, type)

def subclass_check(val, type) -> bool:
    return issubclass(val, type)

#
#
#
T = TypeVar("T")
U = TypeVar("U")

Option = TypeVar("Option")
Condition = TypeVar("Condition")
Result = TypeVar("Result")

class _CheckType(Generic[T]):
    def __getitem__(self, expected_type: type[U]) -> _CheckType[U]: ...
    def __call__(self, arg: T) -> T:
        """
        std.check_type[T](arg)
        checks, that the type of the given argument matches the given T
        """

class _Select(Generic[Result]):
    def __getitem__(self, expected_type: type[U]) -> _Select[U]: ...
    def __call__(
        self, arg, branches: dict[Option, Result], default: Result | None = None
    ) -> Result:
        """
        std.select[T](...) is a type checked wrapper around cohdl.select_with
        equivalent to:

        std.check_type[T](
            cohdl.select_with(
                ...
            )
        )
        """

class _ChooseFirst(Generic[Result]):
    def __getitem__(self, expected_type: type[U]) -> _ChooseFirst[U]: ...
    def __call__(self, *args: tuple[Condition, Result], default: Result) -> Result:
        """
        std.coose_first[T](...) takes an arbitrary number of arguments each of which is a
        tuple with two elements (CONDITION, VALUE). The function returns the first
        VALUE with a truthy CONDITION or default if no such CONDITION exists.
        """

class _Cond(Generic[T]):
    def __getitem__(self, expected_type: type[U]) -> _Cond[U]: ...
    def __call__(self, cond: bool, on_true: T, on_false: T) -> T:
        """
        std.cond[T](cond, on_true, on_false) is a type checked wrapper around
        an if expression equivalent to:

        std.check_type[T](
            on_true if cond else on_false
        )
        """

check_type = _CheckType()
select = _Select()
choose_first = _ChooseFirst()
cond = _Cond()

def check_return(fn):
    """
    the return value of functions decorated with check_return
    is checked against the return type hint
    """

#
#
#

def binary_fold(fn, first, *args): ...
def concat(first, *args) -> BitVector: ...
def stretch(val: Bit | BitVector, factor: int) -> BitVector: ...
def apply_mask(old: BitVector, new: BitVector, mask: BitVector) -> BitVector: ...
