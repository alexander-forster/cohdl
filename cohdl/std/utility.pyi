from __future__ import annotations

from typing import TypeVar, Generic, overload, NoReturn, Literal

from cohdl._core import (
    Entity,
    Bit,
    BitVector,
    Unsigned,
    Signal,
    Port,
    expr_fn,
    AssignMode,
)

from ._assignable_type import AssignableType
from ._core_utility import Value, Ref, nop
from ._context import Duration, Context, SequentialContext

T = TypeVar("T")
U = TypeVar("U")
N = TypeVar(
    "N", Literal[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 16, 20, 24, 32, 64, 100, 128]
)

def add_entity_port(entity: Entity, port: Port, name: str | None = None) -> Port:
    """
    Adds a new port to the given entity.
    """

class Serialized(Generic[T], AssignableType):
    _elemtype_: type[T]

    @classmethod
    def from_raw(cls, raw: BitVector) -> Serialized[T]:
        """
        Create a new instance of `Serialized[T]` that uses `raw`
        as the internal, serialized representation of an object
        of type `T`.
        """

    def _assign_(self, source, mode: AssignMode) -> None: ...
    def value(self, qualifier=Value) -> T:
        """
        Converts the internal, serialized representation into an object of
        type `T` using `std.from_bits` and the optional type qualifier.
        """

    @property
    def ref(self) -> T:
        """
        Converts the internal, serialized representation into an object of
        type `T`. The elements of the returned object are references to
        bits in the serialized representation.

        This only works for types, that are trivially serializable meaning
        each member directly maps to a subrange of the serialized bits.
        Examples for trivially serializable types are
        the builtins Bit/BitVector/Signed/Unsigned, std.SFixed, std.UFixed
        and all std.Record types.

        `self.ref` is equivalent to `self.value(qualifier=std.Ref)`.
        `ref` is implemented as a property to allow its use in assignments.
        """

    def bits(self) -> BitVector:
        """
        Returns the internal, serialized representation.
        My be converted to an instance of `T` using std.from_bits.
        Objects of type `T` can be serialized and assigned to these bits.

        >>> def example(a, b):
        >>>     my_serialized = Signal[Serialized[MyType]](a, b)
        >>>     my_deserialized_1 = my_serialized.value()
        >>>     my_deserialized_2 = std.from_bits[MyType](my_serialized.bits())
        """

def as_readable_vector(*parts: Bit | BitVector) -> Signal[BitVector]:
    """
    Concatenates all arguments to a single BitVector.
    The resulting vector is not writeable because it is assigned
    in the function.

    This function cannot be used in synthesizable contexts.

    >>> def architecture(self):
    >>>     a = Signal[Bit]()
    >>>     b = Signal[BitVector[5]]()
    >>>     c = Signal[Bit]()
    >>>
    >>>     vec = std.as_readable_vector(a, b, c)
    >>>
    >>>     @std.concurrent
    >>>     def logic():
    >>>         assert c == vec[0]
    >>>         assert b == vec[5:1]
    >>>         assert a == vec[6]
    """

def as_writeable_vector(
    *parts: Signal[Bit] | Signal[BitVector], default=None
) -> Signal[BitVector]:
    """
    Takes a list of Bits and BitVectors and creates a new
    BitVector with the total width of all parts.

    Each part is assigned the state of the corresponding
    subsection of this new vector.

    `default` defines the initial state of the new BitVector.

    This function cannot be used in synthesizable contexts.

    >>> def architecture(self):
    >>>     a = Signal[Bit]()
    >>>     b = Signal[BitVector[5]]()
    >>>     c = Signal[Bit]()
    >>>
    >>>     vec = std.as_writeable_vector(a, b, c)
    >>>
    >>>     @std.concurrent
    >>>     def logic():
    >>>         # update the states of a, b and c
    >>>         # by assigning to the corresponding ranges in vec
    >>>         vec[0] <<= Null
    >>>         vec[5:1] <<= Full
    >>>         vec[6] <<= True
    >>>
    >>>         assert c == Bit(Null)
    >>>         assert b == BitVector[5](Full)
    >>>         assert a == Bit(True)
    """

class Array(Generic[T, N]):
    """
    A wrapper utility around cohdl.Array.
    Unlike the builtin cohdl.Array the element type of std.Array is not
    limited to builtins. Any serializable type can be stored.
    """

    def __init__(self, val=None, _qualifier_=Signal): ...
    def __len__(self) -> int:
        """
        returns the number of elements in the Array
        """

    def __getitem__(self, index: Unsigned | int) -> T:
        """
        Returns the element at the given index.

        This only works for trivially serializable element types,
        because internally `std.from_bits[T](raw, std.Ref)` is used
        to obtain the returned value.

        Use `self.get_elem` for other types.
        """

    def get_elem(self, index: Unsigned | int, qualifier=Ref) -> T:
        """
        Returns the value obtained by deserializing the stored element
        at `index` using the given `qualifier`.
        """

    def set_elem(self, index: Unsigned | int, value: T):
        """
        Assign the provided `value` to the element at `index`.
        """

#
#
#

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

def ceil_log_2(inp: int) -> int:
    """
    Return the logarithm to the base 2 of `inp` rounded to the next larger integer.
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
    of wait cycles from it. Because of that, this function can only be
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

    def __init__(
        self,
        *,
        delay: int | None = None,
        rx_delay: int | None = None,
        tx_delay: int | None = None,
    ):
        """
        The optional delay parameters define delay lines for the two internal bit signals.

        When `delay` is set its value is applied to both `rx_delay` and `tx_delay`.

        When `rx_delay` is set to a value greater than zero, the signal set by
        the setter context, is delayed by the specified amount of clock cycles,
        before it is detected in the receiver context. The `rx_delay` is implemented
        in the receiver context.

        `tx_delay` is the opposite of `rx_delay` and specifies a synchronization
        delays for the `clear` operation. This delay is implemented in the sender context.
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
    >>> mailbox = Mailbox[BitVector[8]]()
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

    def __init__(
        self, *, delay: int = None, tx_delay: int = None, rx_delay: int = None
    ):
        """
        Create a Mailbox that can transmit data of the given `type`.
        Internally a `std.SyncFlag` is used to synchronize data access between
        a sending and a receiving context.
        The delay parameters are forwarded to that `std.SyncFlag` and allow for
        basic clock domain crossing.

        `tx_delay` specifies, after how many clock ticks the receiver context
        sees requests set by the sender. (relative to receiver context clock).

        `rx_delay` specifies after how many clock ticks the sender context
        sees acknowledge states set by the receiver. (relative to the sender context clock).
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

class Fifo(Generic[T, N]):
    """
    A first-in-first-out container that can hold up to N-1 elements
    of type T.

    """

    def __init__(self, name: str): ...
    def push(self, data: T):
        """
        push one element onto the Fifo

        may only be called once per clock cycle
        may not be called on a full Fifo
        """

    def pop(self) -> T:
        """
        remove one element from the Fifo
        returns the removed element

        may not be called on an empty Fifo
        """

    def front(self) -> T:
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
