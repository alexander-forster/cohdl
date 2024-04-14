from __future__ import annotations

from typing import Callable

import inspect
import enum

import cohdl
from cohdl import (
    BitSignalEvent,
    Bit,
    Signal,
    evaluated,
    pyeval,
    Variable,
    AssignMode,
)

from cohdl.utility.source_location import SourceLocation

from ._prefix import _Prefix
from ._core_utility import as_awaitable


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
    @pyeval
    def _getter(arg, factor):
        if isinstance(arg, Frequency):
            return arg._val / factor
        return Frequency(arg * factor)

    @pyeval
    def __init__(self, val: int | float | Frequency | Duration):
        if isinstance(val, Duration):
            val = val.frequency()
        if isinstance(val, Frequency):
            val = val._val

        self._val = float(val)

    @pyeval
    def frequency(self) -> Frequency:
        return self

    @pyeval
    def period(self) -> Duration:
        return Duration(1 / self._val)

    @pyeval
    def gigahertz(self) -> float:
        return Frequency._getter(self, 1e9)

    @pyeval
    def megahertz(self) -> float:
        return Frequency._getter(self, 1e6)

    @pyeval
    def kilohertz(self) -> float:
        return Frequency._getter(self, 1e3)

    @pyeval
    def hertz(self) -> float:
        return Frequency._getter(self, 1)

    @pyeval
    def __eq__(self, other: Frequency):
        return self._val == other._val


class Duration:
    @staticmethod
    @pyeval
    def _getter(arg, factor):
        if isinstance(arg, Duration):
            return factor / arg._freq._val
        return Duration(arg / factor)

    @pyeval
    def __init__(self, val: int | float | Frequency | Duration):
        if isinstance(val, Duration):
            self._freq = val._freq
        elif isinstance(val, Frequency):
            self._freq = val
        else:
            self._freq = Frequency(1 / val)

    @pyeval
    def frequency(self) -> Frequency:
        return self._freq

    @pyeval
    def period(self) -> Duration:
        return self

    @pyeval
    def picoseconds(self):
        return Duration._getter(self, 1e12)

    @pyeval
    def nanoseconds(self):
        return Duration._getter(self, 1e9)

    @pyeval
    def microseconds(self):
        return Duration._getter(self, 1e6)

    @pyeval
    def milliseconds(self):
        return Duration._getter(self, 1e3)

    @pyeval
    def seconds(self):
        return Duration._getter(self, 1)

    @pyeval
    def __eq__(self, other: Duration):
        return self._freq == other._freq

    @pyeval
    def count_periods(
        self, subperiod: Duration, *, allowed_delta=1e-9, float_result=False
    ):
        self_ps = self.picoseconds()
        other_ps = subperiod.picoseconds()

        real_result = self_ps / other_ps

        if float_result:
            return real_result
        else:
            rounded = round(real_result)
            assert (
                abs((rounded - real_result) / real_result) <= allowed_delta
            ), f"subperiod does not divide period {real_result=} {rounded=}"
            return rounded

    @pyeval
    def __truediv__(self, other: int | float | Duration):
        if isinstance(other, Duration):
            self_ps = self.picoseconds()
            other_ps = other.picoseconds()
            return self_ps / other_ps
        else:
            return type(self).picoseconds(self.picoseconds() / other)


Period = Duration


class ClockEdge(enum.Enum):
    NEITHER = enum.auto()
    RISING = enum.auto()
    FALLING = enum.auto()
    BOTH = enum.auto()

    @pyeval
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
        period: Duration | int | None = None,
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
        assert "comment" not in attributes, "comment attribute already set"
        attributes["comment"] = comment

    if fn is None:

        def helper(function):
            with cohdl._core._context.Block("", attributes=attributes):
                function()

        return helper
    else:
        with cohdl._core._context.Block("", attributes=attributes):
            fn()


class _NopContextManager:
    def __enter__(self):
        return None

    def __exit__(self, type, value, traceback):
        return None


def _prefix_wrapper(prefix, fn):
    def wrapped():
        with prefix:
            fn()

    return wrapped


def concurrent(
    fn: Callable | None = None,
    *,
    comment=None,
    attributes: dict | None = None,
    capture_lazy: bool = False,
    wrapped_fn=None,
):
    parent_prefix = _Prefix._parent_prefix()

    if parent_prefix is None:
        parent_prefix = _NopContextManager()

    if attributes is None:
        attributes = {}

    if comment is not None:
        assert "comment" not in attributes, "comment attribute already set"
        attributes["comment"] = comment

    if fn is None:

        def wrapper(fn):
            nonlocal wrapped_fn
            wrapped_fn = fn if wrapped_fn is None else wrapped_fn
            cohdl.concurrent_context(
                _prefix_wrapper(parent_prefix, fn),
                name=fn.__name__,
                attributes=attributes,
                source_location=SourceLocation.from_function(wrapped_fn),
                captured_functions=None if capture_lazy else [fn],
            )

        return wrapper

    wrapped_fn = fn if wrapped_fn is None else wrapped_fn

    cohdl.concurrent_context(
        _prefix_wrapper(parent_prefix, fn),
        name=fn.__name__,
        attributes=attributes,
        source_location=SourceLocation.from_function(wrapped_fn),
        captured_functions=None if capture_lazy else [fn],
    )


def _sequential_impl(
    trigger=None,
    /,
    reset=None,
    *,
    step_cond=None,
    comment=None,
    attributes: dict | None = None,
    capture_lazy: bool = False,
    wrapped_fn,
    on_reset=None,
):
    if on_reset is None:
        on_reset = []
    elif not isinstance(on_reset, list):
        on_reset = [on_reset]

    if trigger is None:

        def wrapper(fn):
            _sequential_impl(
                fn,
                reset=reset,
                step_cond=step_cond,
                comment=comment,
                attributes=attributes,
                capture_lazy=capture_lazy,
                wrapped_fn=wrapped_fn,
            )

        return wrapper

    parent_prefix = _Prefix._parent_prefix()

    if parent_prefix is None:
        parent_prefix = _NopContextManager()

    is_coro = inspect.iscoroutinefunction(trigger)

    if attributes is None:
        attributes = {}

    if comment is not None:
        assert "comment" not in attributes, "comment attribute already set"
        attributes["comment"] = comment

    if step_cond is None:
        step_cond = lambda: True

    if inspect.isfunction(trigger) or is_coro:
        wrapped_fn = trigger if wrapped_fn is None else wrapped_fn

        if is_coro:
            callable = coro = trigger()
            fn = None
        else:
            callable = fn = trigger
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
            _prefix_wrapper(parent_prefix, wrapper),
            name=trigger.__name__,
            attributes=attributes,
            source_location=SourceLocation.from_function(wrapped_fn),
            captured_functions=None if capture_lazy else [callable],
        )

        return trigger

    def helper(fn):
        nonlocal wrapped_fn
        wrapped_fn = fn if wrapped_fn is None else wrapped_fn
        is_coro = inspect.iscoroutinefunction(fn)

        if is_coro:
            callable = coro = fn()
        else:
            coro = None
            callable = fn

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
                _prefix_wrapper(parent_prefix, wrapper),
                name=fn.__name__,
                attributes=attributes,
                source_location=SourceLocation.from_function(wrapped_fn),
                captured_functions=None if capture_lazy else [callable],
            )

        elif reset.is_async():

            def wrapper():
                cohdl.sensitivity.list(trigger.signal(), reset.signal())
                if reset:
                    cohdl.reset_context()
                    for reset_fn in on_reset:
                        reset_fn()
                elif trigger:
                    if step_cond():
                        cohdl.reset_pushed()

                        if is_coro:
                            cohdl.coroutine_step(coro)
                        else:
                            fn()

            wrapper.__name__ = fn.__name__

            cohdl.sequential_context(
                _prefix_wrapper(parent_prefix, wrapper),
                name=fn.__name__,
                attributes=attributes,
                source_location=SourceLocation.from_function(wrapped_fn),
                captured_functions=None if capture_lazy else [callable],
            )

        else:

            def wrapper():
                cohdl.sensitivity.list(trigger.signal())
                if trigger:
                    if reset:
                        cohdl.reset_context()
                        for reset_fn in on_reset:
                            reset_fn()
                    elif step_cond():
                        cohdl.reset_pushed()
                        if is_coro:
                            cohdl.coroutine_step(coro)
                        else:
                            fn()

            wrapper.__name__ = fn.__name__

            cohdl.sequential_context(
                _prefix_wrapper(parent_prefix, wrapper),
                name=fn.__name__,
                attributes=attributes,
                source_location=SourceLocation.from_function(wrapped_fn),
                captured_functions=None if capture_lazy else [callable],
            )

    return helper


def sequential(
    trigger=None,
    /,
    reset=None,
    *,
    step_cond=None,
    comment=None,
    on_reset=None,
    attributes: dict | None = None,
    capture_lazy: bool = False,
):
    if isinstance(trigger, Clock):
        return SequentialContext(
            clk=trigger,
            reset=reset,
            step_cond=step_cond,
            comment=comment,
            on_reset=on_reset,
            attributes=attributes,
            capture_lazy=capture_lazy,
        )

    return _sequential_impl(
        trigger,
        reset=reset,
        step_cond=step_cond,
        comment=comment,
        on_reset=on_reset,
        attributes=attributes,
        capture_lazy=capture_lazy,
        wrapped_fn=None,
    )


def concurrent_assign(target, source):
    @concurrent()
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
        ctx: SequentialContext,
        executors_before: list[Executor],
        executors_after: list[Executor],
    ):
        self.ctx = ctx
        self.executors_before = executors_before
        self.executors_after = executors_after


_current_context: SequentialContext | None = None
_current_context_data: _ContextData | None = None


class SequentialContext:
    @staticmethod
    @pyeval
    def current() -> SequentialContext | None:
        return _current_context

    @staticmethod
    @pyeval
    def current_data():
        return _current_context_data

    @staticmethod
    @pyeval
    def _enter_context(ctx: SequentialContext, data: _ContextData | None = None):
        global _current_context, _current_context_data
        _current_context = ctx
        _current_context_data = data

    @staticmethod
    @pyeval
    def _exit_context():
        global _current_context, _current_context_data
        _current_context = None
        _current_context_data = None

    def __init__(
        self,
        clk: Clock,
        reset: Reset | None = None,
        *,
        step_cond=None,
        comment=None,
        on_reset=None,
        attributes: dict | None = None,
        capture_lazy: bool = False,
    ):
        assert isinstance(clk, Clock)
        assert reset is None or isinstance(reset, Reset)

        self._clk = clk
        self._reset = reset
        self._step_cond = step_cond
        self._comment = comment
        self._on_reset = on_reset
        self._attributes = attributes
        self._capture_lazy = capture_lazy

    def copy(self):
        return type(self)(
            clk=self._clk,
            reset=self._reset,
            step_cond=self._step_cond,
            comment=self._comment,
            on_reset=self._on_reset,
            attributes=self._attributes,
            capture_lazy=self._capture_lazy,
        )

    def clk(self):
        return self._clk

    def reset(self):
        return self._reset

    def step_cond(self):
        return self._step_cond

    def with_params(
        self,
        *,
        clk: Clock | None = None,
        reset: Reset | None = None,
        step_cond=None,
        on_reset=None,
    ):
        return SequentialContext(
            clk=self._clk if clk is None else clk,
            reset=self._reset if reset is None else reset,
            step_cond=self._step_cond if step_cond is None else step_cond,
            on_reset=self._on_reset if on_reset is None else on_reset,
            attributes=self._attributes,
        )

    def or_reset(
        self,
        cond: Bit | None = None,
        *,
        expr=None,
        active_low: bool = False,
        is_async: bool | None = None,
    ):
        combined_reset = Signal[Bit]()

        if cond is not None:
            assert (
                expr is None
            ), "the arguments `cond` and `expr` are mutually exclusive"
            expr = lambda: cond
        else:
            assert (
                expr is not None
            ), "the arguments `cond` and `expr` are mutually exclusive"

        if self._reset is None:

            @concurrent
            def logic():
                nonlocal combined_reset
                combined_reset <<= expr()

        else:
            is_async = is_async if is_async is not None else self._reset.is_async()

            @concurrent
            def logic():
                nonlocal combined_reset

                if active_low:
                    # combined is in reset state (low) when one of the inputs is in reset state
                    combined_reset <<= self._reset.active_low_signal() and expr()
                else:
                    # combined is in reset state (high) when one of the inputs is in reset state
                    combined_reset <<= self._reset.active_high_signal() or expr()

        return SequentialContext(
            self._clk,
            Reset(combined_reset, active_low=active_low, is_async=is_async),
            attributes=self._attributes,
        )

    def and_reset(
        self,
        cond: Bit | None = None,
        *,
        expr=None,
        active_low: bool = False,
        is_async: bool | None = None,
    ):
        combined_reset = Signal[Bit]()

        if cond is not None:
            assert (
                expr is None
            ), "the arguments `cond` and `expr` are mutually exclusive"
            expr = lambda: cond
        else:
            assert (
                expr is not None
            ), "the arguments `cond` and `expr` are mutually exclusive"

        if self._reset is None:

            @concurrent
            def logic():
                nonlocal combined_reset
                combined_reset <<= expr()

        else:
            is_async = is_async if is_async is not None else self._reset.is_async()

            @concurrent
            def logic():
                nonlocal combined_reset

                if active_low:
                    combined_reset <<= self._reset.active_low_signal() or expr()
                else:
                    combined_reset <<= self._reset.active_high_signal() and expr()

        return SequentialContext(
            self._clk,
            Reset(combined_reset, active_low=active_low, is_async=is_async),
            attributes=self._attributes,
        )

    def __call__(
        self,
        fn=None,
        *,
        on_reset=None,
        executors: list[Executor] | None = None,
        attributes: dict | None = None,
    ):
        # copy the sequential context so each invocation has a distinct,
        # associated std.SequentialContext
        cpy = self.copy()

        if attributes is None:
            attributes = cpy._attributes
        elif cpy._attributes is not None:
            attributes = {**cpy._attributes, **attributes}
        else:
            pass

        executors = [] if executors is None else executors

        data = _ContextData(
            cpy,
            executors_before=[
                e for e in executors if e._mode is ExecutorMode.immediate_before
            ],
            executors_after=[
                e for e in executors if e._mode is ExecutorMode.immediate_after
            ],
        )

        def convert_executors(executors: list[Executor], mode: ExecutorMode):
            for executor in executors:
                assert executor._mode is mode, "internal error: executor mode mismatch"

                cohdl.coroutine_step(executor.executor_statemachine())

                if not executor._independent:
                    executor._start @= False

        def helper(fn):
            if inspect.iscoroutinefunction(fn):

                def context_fn():
                    cpy._enter_context(cpy, data)
                    convert_executors(
                        data.executors_before, mode=ExecutorMode.immediate_before
                    )
                    cohdl.coroutine_step(fn())
                    convert_executors(
                        data.executors_after, mode=ExecutorMode.immediate_after
                    )
                    cpy._exit_context()

            else:

                def context_fn():
                    cpy._enter_context(cpy, data)
                    convert_executors(
                        data.executors_before, mode=ExecutorMode.immediate_before
                    )
                    fn()
                    convert_executors(
                        data.executors_after, mode=ExecutorMode.immediate_after
                    )
                    cpy._exit_context()

            context_fn.__name__ = fn.__name__
            return _sequential_impl(
                cpy._clk,
                cpy._reset,
                step_cond=cpy._step_cond,
                on_reset=on_reset,
                comment=cpy._comment,
                attributes=attributes,
                capture_lazy=cpy._capture_lazy,
                wrapped_fn=fn,
            )(context_fn)

        if fn is not None:
            return helper(fn)
        else:
            return helper


Context = SequentialContext

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
    Executor wraps a coroutine in a _sequential_impl process
    and provides methods to start the execution from a different
    context.
    """

    @pyeval
    def _check_context(self):
        if not self._mode is ExecutorMode.parallel_process:
            current_ctx = SequentialContext.current()
            current_data = SequentialContext.current_data()
            assert (
                current_ctx is not None
            ), f"Executor with mode {self._mode} can only be used in functions marked with std.SequentialContext"

            if self._mode is ExecutorMode.immediate_before:
                assert (
                    self in current_data.executors_before
                ), "all used executors with mode {ExecutorMode.immediate_before} must be specified in the std.SequentialContext decorator of the enclosing function"
            else:
                assert (
                    self._mode is ExecutorMode.immediate_after
                ), f"invalid executor mode {self._mode}"
                if self not in current_data.executors_after:
                    current_data.executors_after.append(self)

    async def executor_statemachine(self):
        if not self._independent:
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
        else:
            await self._action(*self._args, **self._kwargs)

    @pyeval
    def __init__(
        self,
        ctx: SequentialContext | None,
        mode: ExecutorMode,
        action,
        result=None,
        args: list | None = None,
        kwargs: dict | None = None,
        independent: bool = False,
    ):
        self._mode = mode
        self._ctx = ctx
        self._action = action

        args = args if args is not None else []
        kwargs = kwargs if kwargs is not None else {}

        self._args = args
        self._kwargs = kwargs
        self._result = result
        self._independent = independent

        if ctx is None:
            if not independent:
                self._start = Variable[Bit](False, name="executor_start")
                self._process_ready = Variable[Bit](
                    False, name="executor_process_ready"
                )
        else:
            assert (
                mode is ExecutorMode.parallel_process
            ), "mode must be `parallel_process` because `ctx` was specified"

            if not independent:
                self._start = Signal[Bit](False, name="executor_start")
                self._process_ready = Signal[Bit](False, name="executor_process_ready")

            @ctx
            async def proc():
                await self.executor_statemachine()

    @classmethod
    @pyeval
    def make_parallel(cls, ctx: SequentialContext, action, result, *args, **kwargs):
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
    @pyeval
    def make_after(cls, action, result, *args, **kwargs):
        return cls(
            ctx=None,
            mode=ExecutorMode.immediate_after,
            action=action,
            result=result,
            args=args,
            kwargs=kwargs,
        )

    @classmethod
    @pyeval
    def make_independent_before(cls, action, result, *args, **kwargs):
        return cls(
            ctx=None,
            mode=ExecutorMode.immediate_before,
            action=action,
            result=result,
            args=args,
            kwargs=kwargs,
            independent=True,
        )

    @classmethod
    @pyeval
    def make_independent_after(cls, action, result, *args, **kwargs):
        return cls(
            ctx=None,
            mode=ExecutorMode.immediate_after,
            action=action,
            result=result,
            args=args,
            kwargs=kwargs,
            independent=True,
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

    @cohdl.expr_fn
    def ready(self):
        return self._process_ready and not self._start

    def result(self):
        assert self.ready()
        return self._result.copy()

    def __hash__(self):
        return id(self)


def at_end_of_context(fn):
    Executor.make_independent_after(fn, None)._check_context()
