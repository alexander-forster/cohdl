from __future__ import annotations

from typing import Callable, overload, TypeVar

import enum

import cohdl
from cohdl import BitSignalEvent, Bit, Signal
from cohdl.utility.source_location import SourceLocation

T = TypeVar("T")

class Reset:
    def __init__(
        self,
        signal: cohdl.Signal[cohdl.Bit],
        active_low: bool = False,
        is_async: bool = False,
    ): ...
    def is_async(self) -> bool: ...
    def is_active_low(self) -> bool: ...
    def is_active_high(self) -> bool: ...
    def active_high_signal(self) -> cohdl.Signal[cohdl.Bit]: ...
    def active_low_signal(self) -> cohdl.Signal[cohdl.Bit]: ...
    def signal(self) -> cohdl.Signal[cohdl.Bit]: ...

class Frequency:
    @overload
    def __init__(self, val: int | float):
        """
        create a new Frequency object with a given frequency in Hertz

        note: Frequency also provides classmethods to create
        an object with a frequency specified in kilo/Mega or Gigahertz

        alternatively std.kHz, std.MHz or std.GHz can be used
        """

    @overload
    def __init__(self, val: Frequency):
        """
        create a new Frequency object with the same
        frequency as the given value
        """

    @overload
    def __init__(self, val: Duration):
        """
        create a new Frequency object with a frequency
        corresponding to the given period
        """

    def frequency(self) -> Frequency:
        """
        returns self

        this method exists to make it easier to write code
        that works with both Frequency and Duration objects
        """

    def period(self) -> Duration:
        """
        converts the Frequency to the corresponding Duration
        """

    @overload
    def gigahertz(self: Frequency) -> float:
        """
        returns the frequency in GHz
        """

    @overload
    @staticmethod
    def gigahertz(val: int | float) -> Frequency:
        """
        construct a Frequency with a value given in gigahertz
        """

    @overload
    def megahertz(self: Frequency) -> float:
        """
        returns the frequency in MHz
        """

    @overload
    @staticmethod
    def megahertz(val: int | float) -> Frequency:
        """
        construct a Frequency with a value given in megahertz
        """

    @overload
    def kilohertz(self: Frequency) -> float:
        """
        returns the frequency in kHz
        """

    @overload
    @staticmethod
    def kilohertz(val: int | float) -> Frequency:
        """
        construct a Frequency with a value given in kilohertz
        """

    @overload
    def hertz(self: Frequency) -> float:
        """
        returns the frequency in Hz
        """

    @overload
    @staticmethod
    def hertz(val: int | float) -> Frequency:
        """
        construct a Frequency with a value given in hertz
        """

    def __eq__(self, other: Frequency) -> bool: ...

class Duration:
    @overload
    def __init__(self, val: int | float):
        """
        create a new Duration object with a given duration in seconds

        note: Duration also provides classmethods to create
        an object with a duration specified in pico/nano/micro or milliseconds

        alternatively std.ps, std.ns, std.us, std.ms can be used
        """

    @overload
    def __init__(self, val: Frequency):
        """
        create a new Duration object with a duration
        corresponding to the given frequency
        """

    @overload
    def __init__(self, val: Duration):
        """
        create a new Duration object with the same duration
        as the given value
        """

    def frequency(self) -> Frequency:
        """
        Interprets the `Duration` as the period of a signal
        and returns the corresponding frequency.
        """

    def period(self) -> Duration:
        """
        returns self

        this method exists to make it easier to write code
        that works with both Frequency and Duration objects
        """

    @overload
    def picoseconds(self: Duration) -> float:
        """
        returns the number of picoseconds in the Duration
        """

    @overload
    @staticmethod
    def picoseconds(val: int | float) -> Duration:
        """
        construct a Duration that lasts the given
        number of picoseconds
        """

    @overload
    def nanoseconds(self: Duration) -> float:
        """
        returns the number of nanoseconds in the Duration
        """

    @overload
    @staticmethod
    def nanoseconds(val: int | float) -> Duration:
        """
        construct a Duration that lasts the given
        number of nanoseconds
        """

    @overload
    def microseconds(self: Duration) -> float:
        """
        returns the number of microseconds in the Duration
        """

    @overload
    @staticmethod
    def microseconds(val: int | float) -> Duration:
        """
        construct a Duration that lasts the given
        number of microseconds
        """

    @overload
    def milliseconds(self: Duration) -> float:
        """
        returns the number of milliseconds in the Duration
        """

    @overload
    @staticmethod
    def milliseconds(val: int | float) -> Duration:
        """
        construct a Duration that lasts the given
        number of milliseconds
        """

    @overload
    def seconds(self: Duration) -> float:
        """
        returns the number of seconds in the Duration
        """

    @overload
    @staticmethod
    def seconds(val: int | float) -> Duration:
        """
        construct a Duration that lasts the given
        number of seconds
        """

    def __eq__(self, other: Duration) -> bool: ...
    def count_periods(
        self, subperiod: Duration, *, allowed_delta=1e-9, float_result: bool = False
    ):
        """
        returns the number of sub-periods that fit in the duration of self

        By default the result is obtained by dividing the two period durations
        and rounding to the nearest integer to account for internal floating point
        inaccuracies. `allowed_delta` defines the maximum allowed difference
        between the float division result and the returned integer.

        When `float_result` is set to true the result of the floating point
        division is returned without rounding.
        """

Period = Duration
"""
deprecated: use std.Duration instead of std.Period
"""

class ClockEdge(enum.Enum):
    NEITHER = enum.auto()
    RISING = enum.auto()
    FALLING = enum.auto()
    BOTH = enum.auto()

    def event_type(self) -> BitSignalEvent.Type: ...

class Clock:
    Edge = ClockEdge

    def __init__(
        self,
        clk_signal: cohdl.Signal[cohdl.Bit],
        *,
        active_edge: ClockEdge = ClockEdge.RISING,
        frequency: Frequency | int | None = None,
        period: Duration | int | None = None,
        duty: float = 0.5,
        phase: float = 0.0,
    ): ...
    def is_rising_edge(self) -> bool: ...
    def is_falling_edge(self) -> bool: ...
    def edge(self) -> ClockEdge: ...
    def signal(self) -> cohdl.Signal[cohdl.Bit]: ...
    def frequency(self) -> Frequency: ...
    def period(self) -> Duration: ...
    def duty(self) -> float: ...
    def phase(self) -> float: ...
    def rising(self) -> Clock: ...
    def falling(self) -> Clock: ...
    def both(self) -> Clock: ...

def block(
    fn: Callable | None = None, /, comment=None, attributes: dict | None = None
): ...
def concurrent(
    fn: Callable | None = None,
    *,
    comment: str | None = None,
    attributes: dict | None = None,
    capture_lazy: bool = False,
):
    """
    turns the decorated function into a synthesizeable concurrent context

    When a `comment` is set it will be added to the VHDL representation
    before the converted logic.

    For now the parameters `attributes` and `capture_lazy` are only used
    internally by cohdl.
    """

def sequential(
    clk: Clock,
    /,
    reset: Reset | None = None,
    *,
    step_cond=None,
    comment: str | None = None,
    attributes: dict | None = None,
    capture_lazy: bool = False,
):
    """
    turns the decorated function into a synthesizable sequential context
    equivalent to a VHDL process

    The generated process has roughly the following structure.

    if `clk`:
       if `reset`:
           reset_context()
       elif `step_cond`():
           # run decorated function

    For asynchronous resets the order of `if reset` and `if clk` is swapped.
    If no `step_cond` is defined it is assumed to evaluate to true.

    When a `comment` is set it will be added to the VHDL representation
    before the converted process.

    For now the parameters `attributes` and `capture_lazy` are only used
    internally by cohdl.
    """

def concurrent_assign(target, source):
    """
    signals assigns `source` to `target` in a concurrent context
    """

def concurrent_eval(target, fn, *args, **kwargs):
    """
    calls `fn` with the given `args`/`kwargs` in a concurrent context
    and signal assigns the result to `target`
    """

def concurrent_call(fn, *args, **kwargs):
    """
    calls `fn` with the given `args`/`kwargs` in a concurrent context
    """

class SequentialContext:
    """
    helper type that wraps the arguments of std.sequential in a single object
    """

    @staticmethod
    def current() -> SequentialContext | None:
        """
        returns the currently used context
        or None when no such context exists
        """

    def __init__(
        self,
        clk: Clock,
        reset: Reset | None = None,
        *,
        step_cond: Callable[[], bool] | None = None,
        attributes: dict | None = None,
    ):
        """
        creates an instance of SequentialContext

        when applied to a function it is equivalent to
        | std.sequential(`clk`, `reset`, step_cond=`step_cond`)
        """

    def clk(self) -> Clock:
        """
        returns the instance of Clock
        """

    def reset(self) -> Reset | None:
        """
        returns the instance of Reset
        """

    def step_cond(self) -> Callable[[], bool] | None:
        """
        returns the step cond expression of the context
        """

    def with_params(
        self, *, clk: Clock | None = None, reset: Reset | None = None, step_cond=None
    ) -> SequentialContext:
        """
        returns a copy of self with all supplied parameters changed
        """

    @overload
    def or_reset(
        self,
        cond: Bit | None = None,
        *,
        active_low: bool = False,
        is_async: bool | None = None,
    ) -> SequentialContext:
        """
        Returns a copy of `self` with the reset condition set to the
        result of ORing `cond` with the reset condition of `self`.

        If `self.reset()` is None `cond` is used as the sole reset condition.

        `active_low` determines, which state of `cond` is interpreted as a reset
        condition and is inherited by the returned context.

        When `is_async` is specified it defines the reset behavior of the new
        context, otherwise this value is inherited from the parent.
        """

    @overload
    def or_reset(
        self,
        *,
        expr=None,
        active_low: bool = False,
        is_async: bool | None = None,
    ) -> SequentialContext:
        """
        Returns a copy of `self` with the reset condition set to the
        result of ORing `expr()` with the reset condition of `self`.

        If `self.reset()` is None `expr()` is used as the sole reset condition.

        `active_low` determines, which state of `cond` is interpreted as a reset
        condition and is inherited by the returned context.

        When `is_async` is specified it defines the reset behavior of the new
        context, otherwise this value is inherited from the parent.
        """

    @overload
    def and_reset(
        self,
        cond: Bit | None = None,
        *,
        active_low: bool = False,
        is_async: bool | None = None,
    ) -> SequentialContext:
        """
        Returns a copy of `self` with the reset condition set to the
        result of ANDing `cond` with the reset condition of `self`.

        If `self.reset()` is None `cond` is used as the sole reset condition.

        `active_low` determines, which state of `cond` is interpreted as a reset
        condition and is inherited by the returned context.

        When `is_async` is specified it defines the reset behavior of the new
        context, otherwise this value is inherited from the parent.
        """

    @overload
    def and_reset(
        self,
        *,
        expr=None,
        active_low: bool = False,
        is_async: bool | None = None,
    ) -> SequentialContext:
        """
        Returns a copy of `self` with the reset condition set to the
        result of ANDing `expr()` with the reset condition of `self`.

        If `self.reset()` is None `expr()` is used as the sole reset condition.

        `active_low` determines, which state of `cond` is interpreted as a reset
        condition and is inherited by the returned context.

        When `is_async` is specified it defines the reset behavior of the new
        context, otherwise this value is inherited from the parent.
        """

    def __call__(
        self,
        fn=None,
        *,
        executors: list[Executor] | None = None,
        attributes: dict | None = None,
    ):
        """
        __call__ is defined to be used as a decorator
        that turns the function it is applied to into a sequential context.

        `executors` is an optional list of all Executors used in the context
        it is only needed for Executors with mode `immediate_before`.
        Executors with other modes can be specified but have no effect
        since the context can detect their usage during parsing.
        """

# keep old name Context for now
# might be deprecated in the future
Context = SequentialContext
"""
deprecated: std.Context has been renamed to std.SequentialContext
"""

#
#
#
#

class ExecutorMode(enum.Enum):
    parallel_process = enum.auto()
    immediate_after = enum.auto()
    immediate_before = enum.auto()

class Executor:
    """
    Executor wraps a coroutine in a sequential process
    and provides methods to start the execution from a different
    context.
    """

    def __init__(
        self,
        ctx: SequentialContext | None,
        mode: ExecutorMode,
        action,
        result=None,
        args: list | None = None,
        kwargs: dict | None = None,
    ): ...
    @classmethod
    def make_parallel(
        cls, ctx: SequentialContext, action, result, *args, **kwargs
    ) -> Executor: ...
    @classmethod
    def make_before(cls, action, result, *args, **kwargs) -> Executor: ...
    @classmethod
    def make_after(cls, action, result, *args, **kwargs) -> Executor: ...
    def start(self, *args, **kwargs):
        """
        Start the executor with the given arguments.

        All args/kwargs are signal assigned to the corresponding argument
        specified in the constructor. Since Executor does not inspect the
        signature of the given coroutine function, position and keyword arguments
        must match the definition in __init__.

        It is not necessary to specify all keyword arguments. This makes
        it possible to pass constant parameters, that do not support
        assignments in __init__.
        """

    async def exec(self, *args, **kwargs):
        """
        Start the Executor, wait until the execution is completed
        and return the result value.

        Check the documentation of `start` for limitations of the
        `args` and `kwargs`.
        """

    def ready(self) -> bool:
        """
        Check if the Executor is ready for a call to start/exec.

        The returned Signal is false while the Executor is active or in reset.
        """

    def result(self):
        """
        returns the result of the last execution of the executor
        """
