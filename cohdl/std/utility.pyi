from __future__ import annotations

from typing import TypeVar, Generic, TypeGuard, overload

from cohdl._core import Bit, BitVector, Temporary, Unsigned

from ._context import Duration

T = TypeVar("T")
U = TypeVar("U")

class _TC(Generic[T]):
    def __getitem__(self, t: type[U]) -> _TC[U]: ...
    def __call__(self, arg) -> T | Temporary[T]:
        """
        `tc[T]` is a conversion utility function that creates
        either a temporary or constant object of type `T` depending on the given argument.

        When `arg` is type qualified (Signal/Variable or Temporary)
        the return value is a new Temporary constructed from arg.
        Otherwise a new constant is constructed using the expression `T(arg)`.

        `tc[T]` is used to write code that is constant evaluated when
        possible and only falls back to runtime variable temporaries
        when necessary.
        """

tc = _TC()

#
#
#

def iscouroutinefunction(fn) -> bool: ...
def instance_check(val, type: type[T]) -> TypeGuard[T]: ...
def subclass_check(val, type) -> bool:
    return issubclass(val, type)

#
#
#

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

#
#
#

def max_int(arg: int | Unsigned) -> int:
    """
    returns the largest possible runtime value of `arg`
    for Unsigned values this is 2**width-1
    since integers are runtime constant they are returned unchanged
    """

@overload
async def wait_for(duration: int | Unsigned, *, allow_zero: bool = False) -> None:
    """
    wait for a given number of ticks

    To avoid a runtime check and logic duplication for the rarely needed
    case of waiting zero ticks, `duration` wait_for does not allow
    a value of 0. This can be changed using `allow_zero`.
    """

@overload
async def wait_for(duration: Duration) -> None:
    """
    wait for a given time duration

    wait_for uses `std.Context.current()` to determine the clock period
    of the enclosing synthesizable context and calculates the needed number
    of wait cycles from it. Because of that this function can only be
    used in contexts defined with std.Context.
    """
