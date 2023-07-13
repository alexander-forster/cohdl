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

def const_cond(arg) -> bool:
    """
    Asserts, that the argument is convertible to a compile
    time constant boolean value. And returns that value.

    This function is used to ensure, that if-statements are
    resolved at compile time (similar to VHDL if-generate statements or preprocessor #if blocks in C).

    Note: CoHDL always evaluates if-Statements with constant argument at compile time
    and discards the dead branch without inspecting it. When the
    context compiles `const_cond` has no effect (other than calling arg.__bool__). The purpose of this function is to prevent
    the accidental usage of runtime variables in conditions.
    """

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

def binary_fold(fn, first, *args, right_fold=False):
    """
    similar to pythons `reduce` function and C++ fold expressions

    ---

    binary_fold(fn, 1, 2)

    `fn(1, 2)`

    binary_fold(fn, 1, 2, 3, 4)

    `fn(fn(fn(1, 2), 3), 4)`

    ---

    when only a single argument is given, a copy of it is returned
    and fn is not called

    ---

    when `right_fold` is set to True the order in which arguments
    are passed to `fn`is reversed:

    binary_fold(fn, 1, 2, 3):

    `fn(fn(1, 2), 3)`

    binary_fold(fn, 1, 2, 3, right_fold=True):

    `fn(1, fn(2, 3))`
    """

def concat(first, *args) -> BitVector:
    """
    concatenate all arguments

    this is equivalent to `first @ arg1 @ arg2 @ ...`

    when only one argument is given the return value
    is a new BitVector (even when the argument was a single Bit)
    """

def stretch(val: Bit | BitVector, factor: int) -> BitVector:
    """
    repeat the bits of `val` `factor` times:

    example:

    stretch(Bit('0'), 1)        -> BitVector("0")
    stretch(Bit('1'), 2)        -> BitVector("11")
    stretch(BitVector('10'), 3) -> BitVector("101010")
    """

def apply_mask(old: BitVector, new: BitVector, mask: BitVector) -> BitVector:
    """
    takes three BitVectors of the same length and returns a new
    BitVector of that same length.
    Each result bit is constructed from the corresponding input
    bits according to the following expression:

    `result_bit = new_bit if mask_bit else old_bit`
    """

def as_bitvector(inp: Bit) -> BitVector[0:0]:
    """
    returns a BitVector of length one with the same state as the given input
    """

#
#
#

def max_int(arg: int | Unsigned) -> int:
    """
    returns the largest possible runtime value of `arg`
    - for Unsigned values this is 2**width-1
    - since integers are runtime constant they are returned unchanged
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

class OutShiftRegister:
    def __init__(self, src: BitVector, msb_first=False):
        """
        Initializes a shift register with the current state of `src`.
        `msb_first` defines the order in which the bits will be
        shifted out of the register.
        """
    def set_data(self, data: BitVector):
        """
        Reinitialize the shift register with the given data
        `data` must have the same width as `src` in __init__

        Warning: setting data is a signal assignment
        and will be overwritten if `shift` is called
        after `set_data` in the same clock cycle.
        """
    async def shift_all(self, target: Bit, shift_delayed=True):
        """
        Shift one bit per clock cycle into target until
        the shift register is empty.
        When `shift_delayed` is set to False shifting starts with
        a delay of one clock cycle
        """
    def empty(self):
        """
        Returns True when all bits have been shifted out of the register
        """
    def shift(self):
        """
        Shifts the register by one bit
        and returns the state of the shifted out bit.

        This method can only be called once per clock cycle
        and may not be mixed with `shift_all`.
        """

class InShiftRegister:
    def __init__(self, len: int, msb_first=False):
        """
        Initializes an empty shift register of length `len`.
        `msb_first` defines the order in which the bits will be
        shifted out of the register.
        """
    async def shift_all(self, src: Bit, shift_delayed=False):
        """
        Shift the state of `src` into the shift register
        until it is full.
        When `shift_delayed` is set to True shifting starts with
        a delay of one clock cycle.
        """
    def clear(self):
        """
        Reinitialize the shift register.

        Warning: clearing is a signal assignment
        and will be overwritten if `shift` is called
        after `clear` in the same clock cycle.
        """
    def full(self):
        """
        Returns True when `len` bits of data have been
        shifted into the register.
        """
    def shift(self, src: Bit):
        """
        Shifts one bit from `src` into the register.

        This method can only be called once per clock cycle
        and may not be mixed with `shift_all`.
        """
    def data(self):
        """
        Returns the deserialized data.
        This call is only valid when the register is full.
        """
