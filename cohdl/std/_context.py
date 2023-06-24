from __future__ import annotations

from typing import Callable

import inspect
import enum

import cohdl
from cohdl import BitSignalEvent, SourceLocation


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
            out = cohdl.Signal[cohdl.Bit]()

            @concurrent
            def inv_reset():
                out.next = ~self._signal

            return out
        else:
            return self._signal

    def active_low_signal(self) -> cohdl.Signal[cohdl.Bit]:
        if not self._active_low:
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
    def _getter(arg, factor):
        if isinstance(arg, Frequency):
            return arg._val / factor
        return Frequency(arg * factor)

    def __init__(self, val: int | float | Frequency | Period):
        if isinstance(val, Period):
            val = val.frequency()
        if isinstance(val, Frequency):
            val = val._val

        self._val = float(val)

    def frequency(self) -> Frequency:
        return self

    def period(self) -> Period:
        return Period(1 / self._val)

    def gigahertz(self) -> float:
        return Frequency._getter(self, 1e9)

    def megahertz(self) -> float:
        return Frequency._getter(self, 1e6)

    def kilohertz(self) -> float:
        return Frequency._getter(self, 1e3)

    def hertz(self) -> float:
        return Frequency._getter(self, 1)

    def __eq__(self, other: Frequency):
        return self._val == other._val


class Period:
    @staticmethod
    def _getter(arg, factor):
        if isinstance(arg, Period):
            return factor / arg._freq._val
        return Period(arg / factor)

    def __init__(self, val: int | float | Frequency | Period):
        if isinstance(val, Period):
            self._freq = val._freq
        elif isinstance(val, Frequency):
            self._freq = val
        else:
            self._freq = Frequency(1 / val)

    def frequency(self) -> Frequency:
        return self._freq

    def period(self) -> Period:
        return self

    def picoseconds(self):
        return Period._getter(self, 1e12)

    def nanoseconds(self):
        return Period._getter(self, 1e9)

    def microseconds(self):
        return Period._getter(self, 1e6)

    def milliseconds(self):
        return Period._getter(self, 1e3)

    def seconds(self):
        return Period._getter(self, 1)

    def __eq__(self, other: Period):
        return self._freq == other._freq

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
            assert abs(rounded) <= allowed_delta, "subperiod does not divide period"
            return rounded

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

    def ticks(self, target_frequency: Frequency | Period):
        ...

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
            self._signal, ClockEdge.RISING, self._frequency, self._duty, self._phase
        )

    def falling(self) -> Clock:
        return Clock(
            self._signal,
            ClockEdge.FALLING,
            self._frequency,
            self._duty,
            self._phase,
        )

    def both(self) -> Clock:
        return Clock(
            self._signal, ClockEdge.BOTH, self._frequency, self._duty, self._phase
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
    capture_lazy: bool = False,
    comment=None,
    attributes: dict | None = None,
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
    reset=None,
    capture_lazy: bool = False,
    comment=None,
    attributes: dict | None = None,
):
    is_coro = inspect.iscoroutinefunction(trigger)

    if attributes is None:
        attributes = {}

    if comment is not None:
        assert "comment" not in attributes
        attributes["comment"] = comment

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
            else:
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
                    else:
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
