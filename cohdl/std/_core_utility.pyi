from __future__ import annotations

from typing import (
    TypeVar,
    Generic,
    TypeGuard,
    overload,
    NoReturn,
    Iterable,
    Callable,
    Any,
)

from cohdl._core import (
    Entity,
    Bit,
    BitVector,
    Signed,
    Unsigned,
    Port,
    expr_fn,
    Null,
)

from cohdl._core import Signal as CohdlSignal
from cohdl._core import Variable as CohdlVariable
from cohdl._core import Temporary as CohdlTemporary

from ._context import Duration, Context, SequentialContext

T = TypeVar("T")
U = TypeVar("U")

def nop(*args, **kwargs) -> None:
    """
    A function that takes arbitrary arguments, does nothing and returns None.
    Can be used as a default value for optional callback functions.
    """

def comment(*lines: str) -> None:
    """
    Inserts a comment into the generated VHDL representation.

    std.comment("Hello, world!", "A", "B") is translated into

    >>> -- Hello, world!
    >>> -- A
    >>> -- B
    """

def fail(message: str, *args, **kwargs) -> NoReturn:
    """
    Fail the compilation with an error message.
    `message` is formatted with `args` and `kwargs` because
    f-strings are not supported in synthesizable contexts.
    """

def identity(inp: T, /) -> T:
    """
    returns its argument unchanged
    """

#
#
#

NONLOCAL_TYPE = TypeVar("NONLOCAL_TYPE", type[CohdlSignal], type[CohdlVariable])

class _Nonlocal(Generic[NONLOCAL_TYPE]):
    def __new__(cls, *args, **kwargs) -> NONLOCAL_TYPE: ...

Nonlocal = _Nonlocal

"""
Wrapper utility, that constructs new Signals or Variables
as if it were defined outside the evaluated context.
This can be useful to circumvent the special default-value-semantics
of locally constructed Signals/Variables.

>>> a = Signal[Bit](True)
>>> 
>>> @std.sequential
>>> def process():
>>>     b = Nonlocal[Signal[Bit]](True)
>>>     c = Signal[Bit](True)
>>>     # both a and b are bit signals with a default value of '1'
>>>     # c has no default value but is *immediately* assigned 'True'
>>>     # when it is constructed
"""

PRIMITIVE = TypeVar("PRIMITIVE", Bit, Unsigned, Signed, BitVector)

class _RefQualifierWrapper:
    def __getitem__(self, data_type: type[U]) -> type[U]: ...

class _ValueQualifierWrapper:
    def __getitem__(self, data_type: type[U]) -> type[U]: ...

class _SignalQualifierWrapper:
    @overload
    def __getitem__(
        self, data_type: type[PRIMITIVE]
    ) -> type[CohdlSignal[PRIMITIVE]]: ...
    @overload
    def __getitem__(self, data_type: type[U]) -> type[U]: ...
    @overload
    def __call__(self, arg: PRIMITIVE) -> CohdlSignal[PRIMITIVE]: ...
    @overload
    def __call__(self, arg: U) -> U: ...

class _VariableQualifierWrapper:
    @overload
    def __getitem__(
        self, data_type: type[PRIMITIVE]
    ) -> type[CohdlVariable[PRIMITIVE]]: ...
    @overload
    def __getitem__(self, data_type: type[U]) -> type[U]: ...
    @overload
    def __call__(self, arg: PRIMITIVE) -> CohdlVariable[PRIMITIVE]: ...
    @overload
    def __call__(self, arg: U) -> U: ...

class _TemporaryQualifierWrapper:
    @overload
    def __getitem__(
        self, data_type: type[PRIMITIVE]
    ) -> type[CohdlTemporary[PRIMITIVE]]: ...
    @overload
    def __getitem__(self, data_type: type[U]) -> type[U]: ...
    @overload
    def __call__(self, arg: PRIMITIVE) -> CohdlTemporary[PRIMITIVE]: ...
    @overload
    def __call__(self, arg: U) -> U: ...

Ref: _RefQualifierWrapper
Value: _ValueQualifierWrapper
Signal: _SignalQualifierWrapper
Variable: _VariableQualifierWrapper
Temporary: _TemporaryQualifierWrapper

#
#
#

def iscouroutinefunction(fn, /) -> bool:
    """
    Returns true when fn is a coroutine function
    """

def base_type(val_or_type, /) -> type:
    """
    Determines the type of the given argument after all type qualifiers are removed.

    >>> base_type(int) is int
    >>> base_type(1) is int
    >>> base_type(Signal[Bit]) is Bit
    >>> base_type(Signal[Bit](True)) is Bit
    >>> base_type(Signal[BitVector[7:0]]) is BitVector[8]
    >>> base_type(Signal[Array[Bit, 3]]) is Array[Bit, 3]
    """

def instance_check(val, type: type[T]) -> TypeGuard[T]:
    """
    `instance_check` is similar to Pythons `isinstance`.
    The only difference is that type qualified types (Signals, Variables, Temporaries)
    are decayed before the type check.

    ---
    example:

    >>> isinstance(Bit(), Bit) == True
    >>> instance_check(Bit(), Bit) == True
    >>> isinstance(Signal[Bit](), Bit) == False
    >>> instance_check(Signal[Bit](), Bit) == True
    """

def subclass_check(val, type) -> bool:
    """
    `subclass_check` is similar to Pythons `issubclass`.
    The only difference is that type qualified types (Signals, Variables, Temporaries)
    are decayed before the type check.
    """

async def as_awaitable(fn, /, *args, **kwargs):
    """
    Calls or awaits `fn` with the given arguments.

    `await as_awaitable(fn, a, b=b)` is equivalent to `await fn(a, b=b)` when `fn`is a coroutine function.
    Otherwise the expression is equivalent to `fn(a, b=b)`.
    """

def zeros(len: int) -> BitVector:
    """
    Similar to matlab/numpy zeros.
    Returns a BitVector literal of width `len` with all bits set to `0`.
    """

def ones(len: int) -> BitVector:
    """
    Similar to matlab/numpy ones.
    Returns a BitVector literal of width `len` with all bits set to `1`.
    """

def width(inp: Bit | BitVector) -> int:
    """
    Determines the number of bits in `inp`.
    Returns `1` if `inp` is a bit type and `inp.width` otherwise.
    """

def one_hot(width: int, bit_pos: int | Unsigned) -> BitVector:
    """
    Returns a BitVector of `width` bits where the single bit at index
    `bit_pos` is set to `1`.
    """

def reverse_bits(inp: BitVector) -> BitVector:
    """
    Creates a new BitVector from the Bits in `inp` in reverse order.

    ---

    example:

    >>> reverse_bits(BitVector[5]("10100")) == BitVector[5]("00101")
    """

#
#
#

def is_qualified(arg) -> bool:
    """
    Return true if `arg` is a type qualified value (a Port/Signal, Variable or Temporary).
    """

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
        `std.check_type[T](arg)`
        checks, that the type of the given argument matches the given `T`
        """

class _Select(Generic[Result]):
    def __getitem__(self, expected_type: type[U]) -> _Select[U]: ...
    def __call__(
        self, arg, branches: dict[Option, Result], default: Result | None = None
    ) -> Result:
        """
        `std.select[T](...)` is a type checked wrapper around `cohdl.select_with`
        equivalent to:

        >>> std.check_type[T](
        >>>     cohdl.select_with(
        >>>         ...
        >>>     )
        >>> )
        """

class _ChooseFirst(Generic[Result]):
    def __getitem__(self, expected_type: type[U]) -> _ChooseFirst[U]: ...
    def __call__(self, *args: tuple[Condition, Result], default: Result) -> Result:
        """
        `std.coose_first[T](...)` takes an arbitrary number of arguments each of which is a
        tuple with two elements (CONDITION, VALUE). The function returns the first
        VALUE with a truthy CONDITION or default if no such CONDITION exists.
        """

class _Cond(Generic[T]):
    def __getitem__(self, expected_type: type[U]) -> _Cond[U]: ...
    def __call__(self, cond: bool, on_true: T, on_false: T) -> T:
        """
        `std.cond[T](cond, on_true, on_false)` is a type checked wrapper around
        an if expression equivalent to:

        >>> std.check_type[T](
        >>>     on_true if cond else on_false
        >>> )
        """

check_type = _CheckType()
select = _Select()
choose_first = _ChooseFirst()
cond = _Cond()

#
#
#

def count_bits(inp: type | Any) -> int:
    """
    Returns the number of bits in the serialized representation
    of `inp`. `inp` can be a Bit/BitVector type a custom type
    that defines `_count_bits_` or an instance of such a type.
    """

def to_bits(inp: Bit | BitVector | Any, /) -> BitVector:
    """
    Converts the given argument to a BitVector.
    The result is a new temporary or constant constructed from the argument.

    When `inp` has a type other than Bit/BitVector/Signed/Unsigned it
    must define a method `_to_bits_`, that implements the to_bits operation.

    `std.from_bits` performs the inverse function.

    >>> class ComplexArgs:
    >>>
    >>> class MyComplex:
    >>>     def __init__(self, real: Unsigned[8], imag: )
    """

class _FromBits(Generic[T]):
    def __call__(self, bits: BitVector, qualifier=Value) -> T: ...

class _FromBitsType:
    def __getitem__(self, target: type[T]) -> _FromBits[T]: ...

from_bits = _FromBitsType()

#
#
#

def check_return(fn):
    """
    the return value of functions decorated with check_return
    is checked against the return type hint
    """

#
#
#

def binary_fold(fn: Callable[[Any, Any], Any], args: Iterable, right_fold=False):
    """
    similar to pythons `reduce` function and C++ fold expressions

    ---

    >>> binary_fold(fn, (1, 2))
    >>> # == fn(1, 2)

    >>> binary_fold(fn, (1, 2, 3, 4))
    >>> # == fn(fn(fn(1, 2), 3), 4)

    ---

    when only a single argument is given, a copy of it is returned
    and fn is not called

    ---

    when `right_fold` is set to True the order in which arguments
    are passed to `fn`is reversed:

    >>> binary_fold(fn, (1, 2, 3)):
    >>> # == fn(fn(1, 2), 3)

    >>> binary_fold(fn, (1, 2, 3), right_fold=True):
    >>> # == fn(1, fn(2, 3))
    """

def batched_fold(fn: Callable[[Any, Any], Any], args: Iterable, batch_size=2):
    """
    Alternative to binary_fold for commutative operations.

    - splits args into batches of the given size
    - runs std.binary fold on each batch
    - recursively calls batched_fold on the result until
        only a singe result remains

    ---

    >>> batched_fold(fn, (1, 2, 3, 4, 5, 6, 7), batch_size=2)
    >>> # == fn(
    >>> #        fn(
    >>> #            fn(1, 2),
    >>> #            fn(3, 4)),
    >>> #        fn(
    >>> #            fn(5, 6),
    >>> #            7))
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

    >>> stretch(Bit('0'), 1)           # -> "0"
    >>> stretch(Bit('1'), 2)           # -> "11"
    >>> stretch(BitVector[2]('10'), 3) # -> "111000"
    """

def apply_mask(old: BitVector, new: BitVector, mask: BitVector) -> BitVector:
    """
    takes three BitVectors of the same length and returns a new
    BitVector of that same length.
    Each result bit is constructed from the corresponding input
    bits according to the following expression:

    `result_bit = new_bit if mask_bit else old_bit`
    """

def as_bitvector(inp: BitVector | Bit | str) -> BitVector:
    """
    Returns a BitVector constructed from the argument.

    When `inp` is of possibly qualified type BitVector the result
    is a copy of the input cast to BitVector.

    When `inp` is of possibly qualified type Bit the result is
    a vector of length one with the same state as the bit.

    When `inp` is of type str the result is a bitvector literal
    with the same length as inp.
    """

def rol(inp: BitVector, n: int = 1) -> BitVector:
    """
    roll left `n` bits

    >>> rol(bitvector("1001"))
    >>> "0011"
    >>> rol(bitvector("1001"), 2)
    >>> "0110"
    """

def ror(inp: BitVector, n: int = 1) -> BitVector:
    """
    roll right `n` bits

    >>> ror(bitvector("1001"))
    >>> "1100"
    >>> ror(bitvector("1001"), 2)
    >>> "0110"
    """

def lshift_fill(val: BitVector, fill: Bit | BitVector) -> BitVector:
    """
    Left shift `val` by the width of `fill` and

    >>> lshift_fill(abcdef, XYZ) == defXYZ
    >>> lshift_fill()
    """

def rshift_fill(val: BitVector, fill: Bit | BitVector) -> BitVector:
    """ """

def batched(input: BitVector, n: int) -> list[BitVector]:
    """
    Splits an input vector of length `M` into subvectors of length `n`.
    `M` must be a multiple of `n`.
    The result is a list of BitVectors starting with the least significant slice.
    The elements of the result are references to the corresponding slices of `input`.

    >>> input = BitVector[16]()
    >>> # the following two lines are equivalent
    >>> a = batched(input, 4)
    >>> a = [input[3:0], input[7:4], input[11:8], input[15:12]]
    """

def select_batch(
    input: BitVector, onehot_selector: BitVector, batch_size: int
) -> BitVector:
    """
    Returns a subvector of input using a onehot selector.

    The result is obtained by stretching `onehot_selector` by a factor
    of `batch_size` (see std.stretch) and the following sequence
    of binary-and/binary-or operations.

    >>> # input          abcd efgh ijkl
    >>> # selector   &   0000 1111 0000
    >>> # -----------------------------
    >>> #                0000|efgh|0000 -> efgh

    `len(input)` must be equal to `len(onehot_selector)*batch_size`
    """

def parity(vec: BitVector) -> Bit:
    """
    Returns the parity of a given BitVector
    calculated as a repeated xor operation over
    all bits.
    """
