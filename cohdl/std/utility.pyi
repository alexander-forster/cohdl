from __future__ import annotations

from typing import TypeVar, Generic, TypeGuard, overload, NoReturn

from cohdl._core import (
    Entity,
    Bit,
    BitVector,
    Temporary,
    Unsigned,
    Signal,
    Port,
    expr_fn,
    Null,
)

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

def add_entity_port(entity: Entity, port: Port, name: str | None = None) -> Port:
    """
    Adds a new port to the given entity.
    """

#
#
#

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

    >>> binary_fold(fn, 1, 2)
    >>> # == fn(1, 2)

    >>> binary_fold(fn, 1, 2, 3, 4)
    >>> # == fn(fn(fn(1, 2), 3), 4)

    ---

    when only a single argument is given, a copy of it is returned
    and fn is not called

    ---

    when `right_fold` is set to True the order in which arguments
    are passed to `fn`is reversed:

    >>> binary_fold(fn, 1, 2, 3):
    >>> # == fn(fn(1, 2), 3)

    >>> binary_fold(fn, 1, 2, 3, right_fold=True):
    >>> # == fn(1, fn(2, 3))
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

def stringify(*args, sep: str = ""):
    """
    returns `sep.join(str(arg) for arg in args)`

    This function exists to allow basic string conversions
    in evaluated contexts.
    """

class DelayLine(Generic[T]):
    @overload
    def __init__(self, inp: T, delay: int):
        """
        DelayLine wraps a list of Signals of type T.
        With `delay + 1` elements. When used in a synthesizable context
        the value of each element is assigned to the next one
        every time the constructor is evaluated.

        `initial` defines the default value of the internal memory elements.

        DelayLines can be defined outside of synthesizable contexts,
        when the `ctx` argument is provided.

        >>> line_a = DelayLine(inp, 3, initial=Null ctx=seq_ctx)
        >>>
        >>> @seq_ctx
        >>> def example():
        >>>     line_b = DelayLine(inp, 5)
        >>>
        >>>     out.a <<= line_a.last() # inp delayed by 3
        >>>     out.a <<= line_a[1]     # inp delayed by 1
        >>>
        >>>     out.b <<= line_b.last() # inp delayed by 5
        >>>     out.b <<= line_b[2]     # inp delayed by 2
        """
    @overload
    def __init__(self, inp: T, delay: int, ctx: SequentialContext): ...
    @overload
    def __init__(self, inp: T, delay: int, initial): ...
    @overload
    def __init__(self, inp: T, delay: int, initial, ctx: SequentialContext): ...
    def __getitem__(self, delay: int) -> T: ...
    def __len__(self) -> int: ...
    def __iter__(self): ...
    def last(self) -> T: ...

@overload
def delayed(inp, delay: int, inital) -> Signal:
    """
    Returns a copy of `inp` delayed by a number of clock cycles.

    When `initial` is specified it is passed as the first argument
    of the constructors of the intermediate signals.

    >>>
    >>> @std.sequential(clk)
    >>> def example():
    >>>     out_a <<= std.delayed(inp, 3)
    >>>
    >>>     if update_b:
    >>>         out_b <<= std.delayed(inp, 2)
    >>>
    >>> # output:
    >>>
    >>> inp      : A B C D E F G H I J K L M
    >>> update_b : 0 1 1 1 1 1 0 0 0 1 1 1 1
    >>> ------------------------------------
    >>> out_a    : 0 0 0 A B C D E F G H I J
    >>> out_b    : 0 0 0 B C D D D D E F J K
    >>>
    """

@overload
def delayed(inp, delay: int) -> Signal: ...
def debounce(
    ctx: SequentialContext,
    inp: Signal[Bit],
    period: int | Duration,
    initial: bool | Bit = False,
    allowed_delta: float = 1e-9,
) -> Signal[Bit]:
    """
    Debounce the input signal using a saturating counter
    with a max-value defined by `period`.

    The counter is incremented, when `inp` is '1', and decremented
    when `inp` is '0'.

    The output signal is set to '1', when the max-value
    is reached, and to '0' when 0 is reached.

    On reset, the internal counter is initialized with `period/2`
    and the output is defined by `initial`.

    When `period` is defined as a Duration, `allowed_delta` defines the maximal
    allowed relative error in the debounce period.

    ---
    >>> # Example
    >>> def architecture(self):
    >>>     ctx = std.SequentialContext(self.clk)
    >>>     debounced = std.debounce(ctx, self.inp, 128)
    >>>
    >>>     # output debounced version of self.inp
    >>>     std.concurrent_assign(self.output, debounced)
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

def int_log_2(inp: int) -> int:
    """
    Returns the base two logarithm of a number.
    Asserts, that `inp` is of type int and a power of 2.
    """

def is_pow_two(inp: int):
    """
    check if `inp` is an integer power of two
    """

async def tick() -> None:
    """
    wait for a single clock cycle

    This will introduce an unconditional state transition.

    >>> # the following lines are equivalent
    >>> await std.tick()
    >>> await std.wait_for(1)
    >>> await cohdl.true
    """

@overload
async def wait_for(duration: int | Unsigned, *, allow_zero: bool = False) -> None:
    """
    wait for a given number of ticks

    To avoid a runtime check and logic duplication for the rarely needed
    case of waiting zero ticks, `duration` does not allow
    a value of 0. This can be changed by setting `allow_zero` to true.
    """

@overload
async def wait_for(duration: Duration) -> None:
    """
    wait for a given time duration

    wait_for uses `std.SequentialContext.current()` to determine the clock period
    of the enclosing synthesizable context and calculates the needed number
    of wait cycles from it. Because of that this function can only be
    used in sequential contexts defined with a fixed frequency Clock.
    """

async def wait_forever() -> NoReturn:
    """
    stop execution of the coroutine

    This will introduce a statemachine state with no exit path.
    The only way to leave this function is a reset of the enclosing context.
    """

class Waiter:
    """
    Alternative to std.wait_for, that makes it possible to
    reuse the same counter register for multiple wait operations.
    """

    def __init__(self, max_duration: int | Duration):
        """
        Initialize a Waiter that can wait up to a given duration.
        When `max_duration` is an integer it is interpreted a
        """
    async def wait_for(self, duration: int | Duration):
        """
        same as std.wait_for() but all calls to this method, on
        a single instance of Waiter, use the same counter register.

        `duration` may not exceed the `max_duration` defined in the constructor.
        """

class OutShiftRegister:
    def __init__(self, src: BitVector, msb_first=False, unchecked=False):
        """
        Initializes a shift register with the current state of `src`.
        `msb_first` defines the order in which the bits will be
        shifted out of the register.

        When `unchecked` is set to True no assertions for shifts
        from empty registers are generated. Instead zeros will be
        shifted out. The methods `shift_all` and `empty` cannot be
        used when this option is set.
        """
    def set_data(self, data: BitVector):
        """
        Reinitialize the shift register with the given data
        `data` must have the same width as `src` in __init__

        Warning: setting data is a signal assignment
        and will be overwritten if `shift` is called
        after `set_data` in the same clock cycle.
        """
    async def shift_all(
        self, target: Signal[Bit] | Signal[BitVector], shift_delayed=False
    ):
        """
        On each clock cycle target is updated by shifting
        the corresponding number of bits out of the shift register.
        This coroutine returns once the register is empty.

        When `shift_delayed` is set to True shifting starts with
        a delay of one clock cycle.
        """
    def empty(self):
        """
        Returns True when all bits have been shifted out of the register
        """
    @overload
    def shift(self) -> Bit:
        """
        Shifts the register by one bit
        and returns the state of the shifted out bit.

        This method can only be called once per clock cycle
        and may not be mixed with `shift_all`.
        """
    @overload
    def shift(self, count: int) -> BitVector:
        """
        Shifts the register by `count` bits
        and returns a vector of the shifted out bits.

        This method can only be called once per clock cycle
        and may not be mixed with `shift_all`.
        """

class InShiftRegister:
    def __init__(self, len: int, msb_first=False, unchecked=False):
        """
        Initializes an empty shift register of length `len`.
        `msb_first` defines the order in which the bits will be
        shifted out of the register.

        When `unchecked` is set to True no assertions for shifts
        into full registers are generated. Instead old bits will be
        shifted out. The methods `shift_all` and `full` cannot be
        used when this options is set.
        """
    async def shift_all(self, src: Bit | BitVector, shift_delayed=False):
        """
        Shift the state of `src` into the shift register
        on each clock cycle until it is full.
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
    def shift(self, src: Bit | BitVector):
        """
        Shifts the content of `src` into the register.

        This method can only be called once per clock cycle
        and may not be mixed with `shift_all`.
        """
    def data(self):
        """
        Returns the deserialized data.
        This call is only valid when the register is full.
        """

def continuous_counter(
    ctx: Context, limit: int | Unsigned, *, on_change=nop
) -> Signal[Unsigned]:
    """
    Returns a unsigned signal that is incremented on each tick of `ctx`.
    When `limit` is reached the counter continues from zero.

    `on_change` is an optional callback function. It is invoked every time
    the counter value is updated with the new counter value as the only argument.

    example:

    >>> cnt = std.continuous_counter(ctx, 3)
    >>> # produces the sequence `0-1-2-3-0-1-2-...`
    """

class ToggleSignal:
    def __init__(
        self,
        ctx: Context,
        first_duration: int | Unsigned | Duration,
        second_duration: int | Unsigned | Duration | None = None,
        *,
        default_state: bool = False,
        first_state: bool = False,
        require_enable: bool = False,
        on_rising=None,
        on_falling=None,
    ):
        """
        Defines a bit signal that toggles between `0` and `1` with a defined
        period and duty cycle.

        The duration parameters define how long the signal remains in each state.
        These values are relative to the clock tick of `ctx`. `int` and `Unsigned`
        parameters are interpreted as a number of clock ticks. When a `std.Duration`
        is given, the number of ticks is inferred from the clock of `ctx`
        (so this only works if the clock has a defined frequency).
        `first_duration` and `second_duration` can have different types.

        If only `first_duration` is given the value will be reused for
        `second_duration` creating a signal with 50% duty cycle.

        `default_state` defines the signal state during reset and when
        the ToggleSignal is disabled.

        `first_state` defines the state of the signal when starting after a reset.
        I.e. `first_state=False` produces `XX0101...` whereas `first_state=True` produces `XX1010` where
        `X` is the reset state defined by `default_state`.

        By default the toggle signal starts as soon as the reset condition of `ctx` becomes false.
        When `require_enable` is set to True it will wait until `enable` is called.

        `on_rising` and `on_falling` are optional callback functions. They are invoked
        when ToggleSignal updates the internal state (i.e. in the clock cycle before
        the state change becomes visible to other sequential contexts).
        """
    def get_reset_signal(self) -> Signal[Bit]:
        """
        Returns the signal used to reset the internal toggle mechanism.
        `enable` and `disable` are helper methods that set/reset this signal.
        """
    def enable(self) -> None:
        """
        Start the toggle signal after a previous call to `disable`.
        """
    def disable(self) -> None:
        """
        Stop the toggle signal and reset the internal counter to zero.
        """
    def state(self) -> Signal[Bit]:
        """
        Returns the bit signal that is toggled by this instance of ToggleSignal.
        """
    def rising(self) -> Signal[Bit]:
        """
        Returns a bit signal that is `1` for a single clock cycle after
        each transition of the toggled signal from `0` to `1`.
        """
    def falling(self) -> Signal[Bit]:
        """
        Returns a bit signal that is `1` for a single clock cycle after
        each transition of the toggled signal from `1` to `0`.
        """

class ClockDivider:
    def __init__(
        self,
        ctx: SequentialContext,
        duration: int | Unsigned | Duration,
        *,
        default_state: bool = False,
        tick_at_start: bool = False,
        require_enable: bool = False,
        on_rising=None,
        on_falling=None,
    ):
        """
        ClockDivider takes a SequentialContext and a duration.
        It generates a signal that is high for one clock cycle
        and low for the rest of a period with the given duration.
        """
    def get_reset_signal(self) -> Signal[Bit]:
        """
        Returns the signal used to reset the internal counter mechanism.
        `enable` and `disable` are helper methods that set/reset this signal.
        """
    def enable(self) -> None:
        """
        Start signal generation after a previous call to `disable`.
        """
    def disable(self) -> None:
        """
        Stop signal generation and reset the internal counter to zero.
        """
    def state(self) -> Signal[Bit]:
        """
        Returns the bit signal that is toggled by this instance of ClockDivider.
        """
    def rising(self) -> Signal[Bit]:
        """
        Returns a bit signal that is `1` for a single clock cycle after
        each transition of self.state() from `0` to `1`.
        """
    def falling(self) -> Signal[Bit]:
        """
        Returns a bit signal that is `1` for a single clock cycle after
        each transition of self.state() from `1` to `0`.
        """

class SyncFlag:
    """
    SyncFlag is used to send single bit notifications between two clocked
    contexts.

    ---
    Example:

    >>> # in sender context
    >>> flag.set()
    >>> # optionally wait until flag is cleared by receiver
    >>> await flag.is_clear()
    >>>
    >>> # in receiver context
    >>> # wait until flag is set and clear it
    >>> await flag.receive()

    ---

    SyncFlag can be used as the argument of an `async with` statement.
    The process will wait until the flag becomes set and automatically clears it once
    the with-scope is left.

    >>> flag = SyncFlag()
    >>> async with flag:
    >>>     ...

    is equivalent to

    >>> flag = SyncFlag()
    >>> await flag.is_set()
    >>> ...
    >>> flag.clear()
    """

    def set(self) -> None:
        """
        Set the flag. This has no effect when it is already set.

        This method is used in the sender context.
        """
    def clear(self) -> None:
        """
        Clear the flag. This has no effect  when it is already clear.

        This method should be used in the receiver context
        after a received `set` was processed.
        """
    @expr_fn
    def is_set(self) -> bool:
        """
        Check if the flag is set.

        Note: This method is marked as `expr_fn` and thus awaitable when used as the
        argument of an await expression.
        """
    @expr_fn
    def is_clear(self) -> bool:
        """
        Check if the flag is clear. (opposite of is_set)

        Note: This method is marked as `expr_fn` and thus awaitable when used as the
        argument of an await expression.
        """
    async def receive(self) -> None:
        """
        Wait until the SyncFlag is set and immediately clear it.
        """
    async def __aenter__(self) -> None: ...
    async def __aexit__(self, val, type, traceback) -> None: ...

class Mailbox(Generic[T]):
    """
    Mailbox combines a signal of data with a `std.SyncFlag`.

    A sender process uses the `send` method to write data and
    mark it as valid.

    ---
    Example:

    >>> # in common scope
    >>> mailbox = Mailbox(BitVector[8])
    >>>
    >>> # in sender context
    >>> mailbox.send(data_to_send)
    >>> # optionally wait until flag is cleared by receiver
    >>> await mailbox.is_clear()
    >>>
    >>> # in receiver context
    >>> # wait until flag is set and clear it
    >>> received_data = await flag.receive()
    """

    def __init__(self, type: type[T], *args, **kwargs):
        """
        Create a Mailbox that can transmit data of the given `type`.

        The optional `args`/`kwargs` will be forwarded to the constructor,
        of the internal Signal (of type `type`).
        """
    def send(self, data: T):
        """
        Put data into Mailbox and mark it as valid.
        """
    async def receive(self) -> T:
        """
        Wait until data becomes valid and return it.
        This method clears the valid flag.
        """
    def data(self) -> T:
        """
        Return the contained data.
        The content is only valid when self.is_set() return true.
        """
    @expr_fn
    def is_set(self) -> bool:
        """
        Returns true if the Mailbox contains data.
        """
    @expr_fn
    def is_clear(self) -> bool:
        """
        Returns true when the Mailbox is empty.
        """
    def clear(self) -> None:
        """
        Unset the internal flag. In the next clock cycle `is_clear` will return true.
        `is_set` will return true once the sender writes new data using `send`.
        """

#
#
#

class Fifo:
    def __init__(self, elem_width: int, depth: int):
        """
        construct a new Fifo containing BitVectors of width `elem_width`

        `depth` defines the size of the internal array.
        The Fifo can hold at most `depth`-1 elements.
        """
    def push(self, data: BitVector):
        """
        push one element onto the Fifo

        may only be called once per clock cycle
        may not be called on a full Fifo
        """
    def pop(self) -> BitVector:
        """
        remove one element from the Fifo
        returns the removed element

        may not be called on an empty Fifo
        """
    def front(self) -> BitVector:
        """
        Returns the state of element at the front of the Fifo
        i.e. the next value returned by `pop` without removing it.

        The result is undefined while the Fifo is empty
        """
    def empty(self) -> Bit:
        """
        check if fifo is empty
        """
    def full(self) -> Bit:
        """
        check if fifo is full
        """
