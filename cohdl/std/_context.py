from __future__ import annotations

from typing import Callable

import inspect
import enum

import cohdl
from cohdl import (
    BitSignalEvent,
    SourceLocation,
    Bit,
    Signal,
    evaluated,
    consteval,
    Variable,
    AssignMode,
)


class Reset:
    def __init__(
        self,
        signal: cohdl.Signal[cohdl.Bit],
        active_low: bool = False,
        is_async: bool = False,
    ):
        assert isinstance(signal, cohdl.Signal)
        assert issubclass(signal.type, cohdl.Bit)

        self._signal = signal
        self._active_low = active_low
        self._is_async = is_async

    def __bool__(self):
        if self._active_low:
            return not self._signal
        else:
            return self._signal

    def is_async(self) -> bool:
        return self._is_async

    def is_active_low(self) -> bool:
        return self._active_low

    def is_active_high(self) -> bool:
        return not self._active_low

    def active_high_signal(self) -> cohdl.Signal[cohdl.Bit]:
        if self._active_low:
            if evaluated():
                return ~self._signal
            else:
                out = cohdl.Signal[cohdl.Bit]()

                @concurrent
                def inv_reset():
                    out.next = ~self._signal

                return out
        else:
            return self._signal

    def active_low_signal(self) -> cohdl.Signal[cohdl.Bit]:
        if not self._active_low:
            if evaluated():
                return ~self._signal
            else:
                out = cohdl.Signal[cohdl.Bit]()

                @concurrent
                def inv_reset():
                    out.next = ~self._signal

                return out
        else:
            return self._signal

    def signal(self) -> cohdl.Signal[cohdl.Bit]:
        return self._signal


class Frequency:
    @staticmethod
    @consteval
    def _getter(arg, factor):
        if isinstance(arg, Frequency):
            return arg._val / factor
        return Frequency(arg * factor)

    @consteval
    def __init__(self, val: int | float | Frequency | Period):
        if isinstance(val, Period):
            val = val.frequency()
        if isinstance(val, Frequency):
            val = val._val

        self._val = float(val)

    @consteval
    def frequency(self) -> Frequency:
        return self

    @consteval
    def period(self) -> Period:
        return Period(1 / self._val)

    @consteval
    def gigahertz(self) -> float:
        return Frequency._getter(self, 1e9)

    @consteval
    def megahertz(self) -> float:
        return Frequency._getter(self, 1e6)

    @consteval
    def kilohertz(self) -> float:
        return Frequency._getter(self, 1e3)

    @consteval
    def hertz(self) -> float:
        return Frequency._getter(self, 1)

    @consteval
    def __eq__(self, other: Frequency):
        return self._val == other._val


class Period:
    @staticmethod
    @consteval
    def _getter(arg, factor):
        if isinstance(arg, Period):
            return factor / arg._freq._val
        return Period(arg / factor)

    @consteval
    def __init__(self, val: int | float | Frequency | Period):
        if isinstance(val, Period):
            self._freq = val._freq
        elif isinstance(val, Frequency):
            self._freq = val
        else:
            self._freq = Frequency(1 / val)

    @consteval
    def frequency(self) -> Frequency:
        return self._freq

    @consteval
    def period(self) -> Period:
        return self

    @consteval
    def picoseconds(self):
        return Period._getter(self, 1e12)

    @consteval
    def nanoseconds(self):
        return Period._getter(self, 1e9)

    @consteval
    def microseconds(self):
        return Period._getter(self, 1e6)

    @consteval
    def milliseconds(self):
        return Period._getter(self, 1e3)

    @consteval
    def seconds(self):
        return Period._getter(self, 1)

    @consteval
    def __eq__(self, other: Period):
        return self._freq == other._freq

    @consteval
    def count_periods(
        self, subperiod: Period, *, allowed_delta=1e-9, float_result=False
    ):
        self_ps = self.picoseconds()
        other_ps = subperiod.picoseconds()

        real_result = self_ps / other_ps

        if float_result:
            return real_result
        else:
            rounded = round(real_result)
            assert (
                abs(rounded - real_result) <= allowed_delta
            ), "subperiod does not divide period"
            return rounded

    @consteval
    def __truediv__(self, other: int | float | Period):
        if isinstance(other, Period):
            self_ps = self.picoseconds()
            other_ps = other.picoseconds()
            return self_ps / other_ps
        else:
            return type(self).picoseconds(self.picoseconds() / other)


Duration = Period


class ClockEdge(enum.Enum):
    NEITHER = enum.auto()
    RISING = enum.auto()
    FALLING = enum.auto()
    BOTH = enum.auto()

    @consteval
    def event_type(self) -> BitSignalEvent.Type:
        if self is ClockEdge.RISING:
            return BitSignalEvent.Type.RISING
        elif self is ClockEdge.FALLING:
            return BitSignalEvent.Type.FALLING
        elif self is ClockEdge.BOTH:
            return BitSignalEvent.Type.BOTH_EDGES

        raise AssertionError(f"invalid value {self}")


class Clock:
    Edge = ClockEdge

    def __init__(
        self,
        clk_signal: cohdl.Signal[cohdl.Bit],
        *,
        active_edge: ClockEdge = ClockEdge.RISING,
        frequency: Frequency | int | None = None,
        period: Period | int | None = None,
        duty: float = 0.5,
        phase: float = 0.0,
    ):
        assert isinstance(clk_signal, cohdl.Signal)
        assert issubclass(clk_signal.type, cohdl.Bit)
        assert (
            frequency is None or period is None
        ), "only one of frequency and period can be set"

        self._signal = clk_signal
        self._duty = duty
        self._phase = phase
        self._edge = active_edge

        if frequency is not None:
            self._frequency = Frequency(frequency)
        elif period is not None:
            self._frequency = Frequency(period)
        else:
            self._frequency = None

    def __bool__(self):
        if self._edge is ClockEdge.RISING:
            return cohdl.rising_edge(self._signal)
        elif self._edge is ClockEdge.FALLING:
            return cohdl.falling_edge(self._signal)
        elif self._edge is ClockEdge.BOTH:
            return cohdl.rising_edge(self._signal) | cohdl.falling_edge(self._signal)
        else:
            raise AssertionError("invalid clock edge")

    def is_rising_edge(self) -> bool:
        return self._edge is ClockEdge.RISING

    def is_falling_edge(self) -> bool:
        return self._edge is ClockEdge.FALLING

    def duration_ticks(self, duration: Duration):
        clk_duration = self._frequency.period()
        return duration // clk_duration

    def edge(self):
        return self._edge

    def signal(self) -> cohdl.Signal[cohdl.Bit]:
        return self._signal

    def frequency(self):
        return self._frequency

    def period(self):
        return self._frequency.period()

    def duty(self):
        return self.duty

    def phase(self):
        return self.phase

    def rising(self) -> Clock:
        return Clock(
            self._signal,
            active_edge=ClockEdge.RISING,
            frequency=self._frequency,
            duty=self._duty,
            phase=self._phase,
        )

    def falling(self) -> Clock:
        return Clock(
            self._signal,
            active_edge=ClockEdge.FALLING,
            frequency=self._frequency,
            duty=self._duty,
            phase=self._phase,
        )

    def both(self) -> Clock:
        return Clock(
            self._signal,
            active_edge=ClockEdge.BOTH,
            frequency=self._frequency,
            duty=self._duty,
            phase=self._phase,
        )


def block(fn: Callable | None = None, /, comment=None, attributes: dict | None = None):
    if attributes is None:
        attributes = {}

    if comment is None:
        assert "comment" not in attributes
        attributes["comment"] = comment

    if fn is None:

        def helper(function):
            with cohdl._core._context.Block("", attributes=attributes):
                function()

        return helper
    else:
        with cohdl._core._context.Block("", attributes=attributes):
            fn()


def concurrent(
    fn: Callable | None = None,
    *,
    comment=None,
    attributes: dict | None = None,
    capture_lazy: bool = False,
):
    if attributes is None:
        attributes = {}

    if comment is not None:
        assert "comment" not in attributes
        attributes["comment"] = comment

    if fn is None:

        def wrapper(fn):
            cohdl.concurrent_context(
                fn,
                name=fn.__name__,
                capture_lazy=capture_lazy,
                attributes=attributes,
                source_location=SourceLocation.from_function(fn),
            )

        return wrapper

    cohdl.concurrent_context(
        fn,
        name=fn.__name__,
        capture_lazy=capture_lazy,
        attributes=attributes,
        source_location=SourceLocation.from_function(fn),
    )


def sequential(
    trigger,
    /,
    reset=None,
    *,
    step_cond=None,
    comment=None,
    attributes: dict | None = None,
    capture_lazy: bool = False,
):
    is_coro = inspect.iscoroutinefunction(trigger)

    if attributes is None:
        attributes = {}

    if comment is not None:
        assert "comment" not in attributes
        attributes["comment"] = comment

    if step_cond is None:
        step_cond = lambda: True

    if inspect.isfunction(trigger) or is_coro:
        if is_coro:
            coro = trigger()
            fn = None
        else:
            fn = trigger
            coro = None

        def wrapper():
            cohdl.sensitivity.all()
            cohdl.reset_pushed()

            if is_coro:
                cohdl.coroutine_step(coro)
            elif step_cond():
                fn()

        wrapper.__name__ = trigger.__name__

        cohdl.sequential_context(
            wrapper,
            capture_lazy=capture_lazy,
            attributes=attributes,
            source_location=SourceLocation.from_function(trigger),
        )

        return trigger

    def helper(fn):
        is_coro = inspect.iscoroutinefunction(fn)

        if is_coro:
            coro = fn()
        else:
            coro = None

        if reset is None:

            def wrapper():
                cohdl.sensitivity.list(trigger.signal())
                if trigger:
                    if step_cond():
                        cohdl.reset_pushed()

                        if is_coro:
                            cohdl.coroutine_step(coro)
                        else:
                            fn()

            wrapper.__name__ = fn.__name__

            cohdl.sequential_context(
                wrapper,
                capture_lazy=capture_lazy,
                attributes=attributes,
                source_location=SourceLocation.from_function(fn),
            )

        elif reset.is_async():

            def wrapper():
                cohdl.sensitivity.list(trigger.signal(), reset.signal())
                if reset:
                    cohdl.reset_context()
                elif trigger:
                    if step_cond():
                        cohdl.reset_pushed()

                        if is_coro:
                            cohdl.coroutine_step(coro)
                        else:
                            fn()

            wrapper.__name__ = fn.__name__

            cohdl.sequential_context(
                wrapper,
                capture_lazy=capture_lazy,
                attributes=attributes,
                source_location=SourceLocation.from_function(fn),
            )

        else:

            def wrapper():
                cohdl.sensitivity.list(trigger.signal())
                if trigger:
                    if reset:
                        cohdl.reset_context()
                    elif step_cond():
                        cohdl.reset_pushed()
                        if is_coro:
                            cohdl.coroutine_step(coro)
                        else:
                            fn()

            wrapper.__name__ = fn.__name__

            cohdl.sequential_context(
                wrapper,
                capture_lazy=capture_lazy,
                attributes=attributes,
                source_location=SourceLocation.from_function(fn),
            )

    return helper


def concurrent_assign(target, source):
    @concurrent(comment="my comment for concurrent_assign")
    def logic():
        nonlocal target
        target <<= source


def concurrent_eval(target, fn, *args, **kwargs):
    @concurrent
    def logic():
        nonlocal target
        target <<= fn(*args, **kwargs)


def concurrent_call(fn, *args, **kwargs):
    @concurrent
    def logic():
        fn(*args, **kwargs)


class _ContextData:
    def __init__(
        self,
        ctx: Context,
        executors_before: list[Executor],
        executors_after: list[Executor],
    ):
        self.ctx = ctx
        self.executors_before = executors_before
        self.executors_after = executors_after


_current_context: Context | None = None
_current_context_data: _ContextData | None = None


class Context:
    @staticmethod
    @consteval
    def current() -> Context | None:
        return _current_context

    @staticmethod
    @consteval
    def current_data():
        return _current_context_data

    @staticmethod
    @consteval
    def _enter_context(ctx: Context, data: _ContextData | None = None):
        global _current_context, _current_context_data
        _current_context = ctx
        _current_context_data = data

    @staticmethod
    @consteval
    def _exit_context():
        global _current_context, _current_context_data
        _current_context = None
        _current_context_data = None

    def __init__(self, clk: Clock, reset: Reset | None = None, *, step_cond=None):
        assert isinstance(clk, Clock)
        assert reset is None or isinstance(reset, Reset)

        self._clk = clk
        self._reset = reset
        self._step_cond = step_cond

    def clk(self):
        return self._clk

    def reset(self):
        return self._reset

    def step_cond(self):
        return self._step_cond

    def with_params(
        self, *, clk: Clock | None = None, reset: Reset | None = None, step_cond=None
    ):
        return Context(
            clk=self._clk if clk is None else clk,
            reset=self._reset if reset is None else reset,
            step_cond=self._step_cond if step_cond is None else step_cond,
        )

    def or_reset(
        self,
        cond: Bit | None = None,
        *,
        expr=None,
        active_low: bool | None = None,
        is_async: bool | None = None,
    ):
        combined_reset = Signal[Bit]()

        if cond is not None:
            assert expr is None
            expr = lambda: cond
        else:
            assert expr is not None

        if self._reset is None:

            @concurrent
            def logic():
                nonlocal combined_reset
                combined_reset <<= expr()

        else:
            active_low = (
                active_low if active_low is not None else self._reset.is_active_low()
            )
            is_async = is_async if is_async is not None else self._reset.is_async()

            @concurrent
            def logic():
                nonlocal combined_reset
                combined_reset <<= self._reset.active_high_signal() or expr()

        return Context(
            self._clk,
            Reset(combined_reset, active_low=active_low, is_async=is_async),
        )

    def and_reset(
        self,
        cond: Bit | None = None,
        *,
        expr=None,
        active_low: bool | None = None,
        is_async: bool | None = None,
    ):
        combined_reset = Signal[Bit]()

        if cond is not None:
            assert expr is None
            expr = lambda: cond
        else:
            assert expr is not None

        if self._reset is None:

            @concurrent
            def logic():
                nonlocal combined_reset
                combined_reset <<= expr()

        else:
            active_low = (
                active_low if active_low is not None else self._reset.is_active_low()
            )
            is_async = is_async if is_async is not None else self._reset.is_async()

            @concurrent
            def logic():
                nonlocal combined_reset
                combined_reset <<= self._reset.active_high_signal() and expr()

        return Context(
            self._clk,
            Reset(combined_reset, active_low=active_low, is_async=is_async),
        )

    def __call__(self, fn=None, *, executors: list[Executor] | None = None):
        executors = [] if executors is None else executors

        data = _ContextData(
            self,
            executors_before=[
                e for e in executors if e._mode is ExecutorMode.immediate_before
            ],
            executors_after=[
                e for e in executors if e._mode is ExecutorMode.immediate_after
            ],
        )

        def convert_executors(executors: list[Executor], mode: ExecutorMode):
            for executor in executors:
                assert executor._mode is mode

                cohdl.coroutine_step(executor.executor_statemachine())
                executor._start @= False

        def helper(fn):
            if inspect.iscoroutinefunction(fn):

                def context_fn():
                    self._enter_context(self, data)
                    convert_executors(
                        data.executors_before, mode=ExecutorMode.immediate_before
                    )
                    cohdl.coroutine_step(fn())
                    convert_executors(
                        data.executors_after, mode=ExecutorMode.immediate_after
                    )
                    self._exit_context()

            else:

                def context_fn():
                    self._enter_context(self, data)
                    convert_executors(
                        data.executors_before, mode=ExecutorMode.immediate_before
                    )
                    fn()
                    convert_executors(
                        data.executors_after, mode=ExecutorMode.immediate_after
                    )
                    self._exit_context()

            return sequential(self._clk, self._reset, step_cond=self._step_cond)(
                context_fn
            )

        if fn is not None:
            return helper(fn)
        else:
            return helper


#
#
#
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

    @consteval
    def _check_context(self):
        if not self._mode is ExecutorMode.parallel_process:
            current_ctx = Context.current()
            current_data = Context.current_data()
            assert (
                current_ctx is not None
            ), "Executor with mode {self._mode} can only be used in functions marked with std.Context"

            if self._mode is ExecutorMode.immediate_before:
                assert (
                    self in current_data.executors_before
                ), "all used executors with mode {ExecutorMode.immediate_before} must be specified in the std.Context decorator of the enclosing function"
            else:
                assert self._mode is ExecutorMode.immediate_after
                if self not in current_data.executors_after:
                    current_data.executors_after.append(self)

    async def executor_statemachine(self):
        while not self._start:
            self._process_ready._assign_(True, AssignMode.AUTO)
        self._process_ready._assign_(False, AssignMode.AUTO)

        if self._result is None:
            await self._action(*self._args, **self._kwargs)
        else:
            self._result._assign_(
                await self._action(*self._args, **self._kwargs), AssignMode.AUTO
            )
        self._process_ready._assign_(True, AssignMode.AUTO)

    def __init__(
        self,
        ctx: Context | None,
        mode: ExecutorMode,
        action,
        result=None,
        args: list | None = None,
        kwargs: dict | None = None,
    ):
        self._mode = mode
        self._ctx = ctx
        self._action = action

        args = args if args is not None else []
        kwargs = kwargs if kwargs is not None else {}

        self._args = args
        self._kwargs = kwargs
        self._result = result

        if ctx is None:
            self._start = Variable[Bit](False, name="executor_start")
            self._process_ready = Variable[Bit](False, name="executor_process_ready")
        else:
            assert mode is ExecutorMode.parallel_process

            self._start = Signal[Bit](False, name="executor_start")
            self._process_ready = Signal[Bit](False, name="executor_process_ready")

            @ctx
            async def proc():
                await self.executor_statemachine()

    @classmethod
    def make_parallel(cls, ctx: Context, action, result, *args, **kwargs):
        return cls(
            ctx=ctx,
            mode=ExecutorMode.parallel_process,
            action=action,
            result=result,
            args=args,
            kwargs=kwargs,
        )

    @classmethod
    def make_before(cls, action, result, *args, **kwargs):
        return cls(
            ctx=None,
            mode=ExecutorMode.immediate_before,
            action=action,
            result=result,
            args=args,
            kwargs=kwargs,
        )

    @classmethod
    def make_after(cls, action, result, *args, **kwargs):
        return cls(
            ctx=None,
            mode=ExecutorMode.immediate_after,
            action=action,
            result=result,
            args=args,
            kwargs=kwargs,
        )

    def start(self, *args, **kwargs):
        self._check_context()
        assert self.ready()
        assert len(self._args) == len(args)

        for target, src in zip(self._args, args):
            target._assign_(src, AssignMode.AUTO)

        for name, val in kwargs.items():
            self._kwargs[name]._assign_(val, AssignMode.AUTO)

        if self._mode is ExecutorMode.parallel_process:
            self._start ^= True
        else:
            self._start @= True

    async def exec(self, *args, **kwargs):
        self._check_context()
        assert self.ready()
        self.start(*args, **kwargs)
        await self.ready()

        if self._result is not None:
            return self._result.copy()
        else:
            return None

    def ready(self):
        return self._process_ready and not self._start

    def result(self):
        assert self.ready()
        return self._result.copy()

    def __hash__(self):
        return id(self)
