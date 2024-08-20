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

from cohdl._core import Entity, Bit, BitVector, Signed, Unsigned, AssignMode

from cohdl._core import Signal as CohdlSignal
from cohdl._core import Variable as CohdlVariable
from cohdl._core import Temporary as CohdlTemporary

from ._context import Duration, Context, SequentialContext

class Null: ...
class Full: ...

T = TypeVar("T")
U = TypeVar("U")

SupportsGt = TypeVar("SupportsGt")
SupportsLt = TypeVar("SupportsLt")
ConvertibleToT = TypeVar("ConvertibleToT")

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

def assign(target, source, mode: AssignMode = AssignMode.AUTO):
    """
    Assign the source value to target using the specified mode.
    Used for generic code where the assignment operator (<<=, @= or ^=)
    depends on the context the operation is used in.

    Equivalent to:
    >>> target._assign_(source, mode)
    """

def as_pyeval(fn, /, *args, **kwargs):
    """
    Calls `fn` with the provided arguments.
    When used in a synthesizable context `fn` will be evaluated
    using the python interpreter. CoHDL will not trace the function.
    """
    return fn(*args, **kwargs)

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

def regenerate_defaults(fn, /):
    """
    When functions are decorated with `std.regenerate_defaults` the default
    arguments are regenerated every time it is called.
    This is different from the normal python behavior where the defaults
    are generated once when the function is declared.

    >>>
    >>> def normal(arg = [1, 2, 3]):
    >>>     return arg
    >>>
    >>> @std.regenerate_defaults
    >>> def decorated(arg = [1, 2, 3]):
    >>>     return arg
    >>>
    >>> normal_a = normal()
    >>> normal_b = normal()
    >>>
    >>> decorated_a = decorated()
    >>> decorated_b = decorated()
    >>>
    >>> assert normal_a is normal_b
    >>> assert decorated_a is not decorated_b
    """
    return fn

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
"""
std.Ref is a pseudo type qualifier. When applied to a primitive
object (Bit, BitVector, Signed, Unsigned, Array), it returns its argument unchanged.
For other types, std.Ref attempts to construct a deep copy with std.Ref applied to all members.
"""

Value: _ValueQualifierWrapper
"""
std.Value is a pseudo type qualifier. It returns a read only copy of its argument.
If the argument is a literal type, it is returned directly, otherwise a new Temporary
is constructed.
"""

Signal: _SignalQualifierWrapper
"""
std.Signal is an alias to cohdl.Signal
"""

Variable: _VariableQualifierWrapper
"""
std.Variable is an alias to cohdl.Variable
"""

Temporary: _TemporaryQualifierWrapper
"""
std.Temporary is an alias to cohdl.Temporary
"""

NoresetSignal: _SignalQualifierWrapper
"""
constructs Signals with the `noreset` argument set to True
"""

NoresetVariable: _VariableQualifierWrapper
"""
constructs Variable with the `noreset` argument set to True
"""

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

def is_one_hot(inp: BitVector) -> Bit:
    """
    Returns '1' if a single bit in `inp` is `1` otherwise `0`.
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
"""
`std.check_type[T](arg)`
checks, that the type of the given argument matches the given `T`
"""

select = _Select()
"""
`std.select[T](...)` is a type checked wrapper around `cohdl.select_with`
equivalent to:

>>> std.check_type[T](
>>>     cohdl.select_with(
>>>         ...
>>>     )
>>> )
"""

choose_first = _ChooseFirst()
"""
`std.coose_first[T](...)` takes an arbitrary number of arguments each of which is a
tuple with two elements (CONDITION, VALUE). The function returns the first
VALUE with a truthy CONDITION or default if no such CONDITION exists.
"""

cond = _Cond()
"""
`std.cond[T](cond, on_true, on_false)` is a type checked wrapper around
an if expression equivalent to:

>>> std.check_type[T](
>>>     on_true if cond else on_false
>>> )
"""

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
    Alternative to binary_fold optimized for associative operations.

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

def repeat(val: Bit | BitVector, times: int) -> BitVector:
    """
    Repeat `val` `times` times:

    example:

    >>> repeat(Bit('0'), 1)            # -> "0"
    >>> repeat(Bit('1'), 3)            # -> "111"
    >>> repeat(BitVector[3]('110'), 2) # -> "110110"
    """

def stretch(val: Bit | BitVector, factor: int) -> BitVector:
    """
    Repeat each Bit of `val` `factor` times:

    example:

    >>> stretch(Bit('0'), 1)           # -> "0"
    >>> stretch(Bit('1'), 2)           # -> "11"
    >>> stretch(BitVector[2]('10'), 3) # -> "111000"
    """

@overload
def leftpad(inp: BitVector, result_width: int) -> BitVector:
    """
    Add null-bits to the left of `inp` until `result_width` is reached.
    """

@overload
def leftpad(inp: BitVector, result_width: int, fill: Bit | Null | Full) -> BitVector:
    """
    Add `fill` bits to the left of `inp` until `result_width` is reached.
    """

@overload
def rightpad(inp: BitVector, result_width: int) -> BitVector:
    """
    Add null-bits to the right of `inp` until `result_width` is reached.
    """

@overload
def rightpad(inp: BitVector, result_width: int, fill: Bit | Null | Full) -> BitVector:
    """
    Add `fill` bits to the right of `inp` until `result_width` is reached.
    """

def pad(
    inp: BitVector, left: int = 0, right: int = 0, fill: Bit | Null | Full = Null
) -> BitVector:
    """
    pad `inp` using the bit specified by `fill`

    `left` and `right` define how often `fill` is added at the respective side
    of `inp`. `fill` defaults to Bit("0").

    >>> def example():
    >>>     vec = BitVector[4]("XXXX")
    >>>     assert std.pad(vec, left=1, right=2) == BitVector[7]("0XXXX00")
    >>>     assert std.pad(vec, left=2, fill=Bit(True)) == BitVector[6]("11XXXX")
    """

def apply_mask(old: BitVector, new: BitVector, mask: BitVector) -> BitVector:
    """
    takes three BitVectors of the same length and returns a new
    BitVector of that same length.
    Each result bit is constructed from the corresponding input
    bits according to the following expression:

    `result_bit = new_bit if mask_bit else old_bit`
    """

class Mask:
    def __init__(self, val: BitVector | Null | Full): ...
    def apply(self, old: BitVector, new: BitVector) -> BitVector:
        """
        Produce a new BitVector by choosing bits from `old` or `new` according to the mask.
        """

    def as_vector(self, width: int) -> BitVector:
        """
        Shorthand for `self.apply(std.zeros(width), std.ones(width))`.
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
    Concatenate `val` and `full` and drop msbs from the result
    so its width matches that of `val`.

    >>> lshift_fill(abcdef, XYZ) == defXYZ
    """

def rshift_fill(val: BitVector, fill: Bit | BitVector) -> BitVector:
    """
    Concatenate `fill` and `val` and drop lsbs from the result
    so its width matches that of `val`.

    >>> rshift_fill(abcdef, XYZ) == XYZabc
    """

def batched(input: BitVector, n: int, allow_partial: bool = False) -> list[BitVector]:
    """
    Splits an input vector of length `M` into subvectors of length `n`.
    `M` must be a multiple of `n` unless `allow_partial` is set to True.
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

@overload
def minimum(
    elements: Iterable[T],
    key: Callable[[T], SupportsLt] = identity,
    cmp: Callable[[T, T], bool] = lambda a, b: a < b,
) -> T: ...
@overload
def minimum(
    *args: T,
    key: Callable[[T], SupportsLt] = identity,
    cmp: Callable[[T, T], bool] = lambda a, b: a < b,
) -> T:
    """
    Synthesizable alternative to Pythons builtin `min` function.

    When only a single positional argument is specified, it is
    interpreted as an iterable and its minimal value is returned.

    When multiple positional arguments are specified, their minimum is returned.

    The function specified by the `key` parameter is used to extract
    an comparison key for each element (see documentation of the Python `min` function).

    The `cmp` parameter defines the function used to compare elements.
    `cmp` takes two positional arguments and is expected to return
    True when the first is smaller than the second.
    """

@overload
def maximum(
    elements: Iterable[T],
    /,
    *,
    key: Callable[[T], SupportsGt] = identity,
    cmp: Callable[[T, T], bool] = lambda a, b: a > b,
) -> T: ...
@overload
def maximum(
    *args: T,
    key: Callable[[T], SupportsGt] = identity,
    cmp: Callable[[T, T], bool] = lambda a, b: a > b,
) -> T:
    """
    Synthesizable alternative to Pythons builtin `max` function.

    See description if `std.minimum`.
    """

def min_element(
    container: Iterable[T],
    /,
    *,
    key: Callable[[T], SupportsLt] = identity,
    cmp: Callable[[T, T], bool] = lambda a, b: a < b,
) -> tuple[Unsigned, T]:
    """
    Finds the smallest element in the given `container` and returns
    a tuple consisting of the index where the element was found and
    a copy of the element.

    The `key` and `cmp` parameters have the same meaning
    as in `std.minimum`.

    >>> U = Unsigned[4]
    >>> l = [U(4), U(2), U(1), U(9), U(1), U(11)]
    >>> idx, elem = std.min_element(l)
    >>>
    >>> assert idx == 2
    >>> assert elem == 1
    """

def max_element(
    container: Iterable[T],
    /,
    *,
    key: Callable[[T], SupportsGt] = identity,
    cmp: Callable[[T, T], bool] = lambda a, b: a > b,
) -> tuple[Unsigned, T]:
    """
    See `std.min_element`.
    """

def min_index(
    container: Iterable[T],
    /,
    *,
    key: Callable[[T], SupportsLt] = identity,
    cmp: Callable[[T, T], bool] = lambda a, b: a < b,
) -> Unsigned:
    """
    Finds the index of the smallest element in the given `container`.
    Unlike the minimum and min_element functions, this one does not have
    to propagate all values. Instead, the keys are computed only once and then
    used for all comparisons. This can be more efficient for large types with
    small keys.
    """

def max_index(
    container: Iterable[T],
    /,
    *,
    key: Callable[[T], SupportsGt] = identity,
    cmp: Callable[[T, T], bool] = lambda a, b: a > b,
) -> Unsigned:
    """
    Finds the index of the largest element in the given `container`.
    See `std.min_index`.
    """

@overload
def count(container: Iterable, /, value) -> Unsigned: ...
@overload
def count(container: Iterable[T], *, check: Callable[[T], bool | Bit]) -> Unsigned:
    """
    Counts how often a value occurs in the `container`.

    The overload with `value` counts all elements comparing equal to it.

    The overload with `check` uses the return value of that callable
    to determine if an element should be counted.
    """

def count_set_bits(vector: BitVector, /, *, batch_size: int = 6) -> Unsigned:
    """
    Returns the number of '1' bits in `vector`.

    `batch_size` is an optional tuning parameter used to improve
    the algorithm. It does not affect the output. Ideally it should
    be set to the input size of LUTs available on the FPGA.
    """

def count_clear_bits(vector: BitVector, /, *, batch_size: int = 6) -> Unsigned:
    """
    Returns the number of '0' bits in `vector`.
    See `count_set_bits` for more information.
    """

def clamp(
    val: T, /, low: ConvertibleToT, high: ConvertibleToT, cmp=lambda a, b: a < b
) -> T:
    """
    Compares `val`, `low` and `high` using `cmp`.
    Returns
        - `val` if it is in the range [low, high].
        - `low` if `val` is less than `low`
        - `high` if `val` is greater than `high`

    The two bound values are converted to the type of `val`
    before the comparison is performed.

    `cmp` takes two positional arguments and should return True
    when the first is smaller than the second.
    """
