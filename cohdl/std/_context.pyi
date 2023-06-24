from __future__ import annotations

from typing import Callable, overload, TypeVar

import enum

import cohdl
from cohdl import BitSignalEvent, SourceLocation

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
    def __init__(self, val: Period):
        """
        create a new Frequency object with a frequency
        corresponding to the given period
        """
    def frequency(self) -> Frequency:
        """
        returns self

        this method exists to make it easier to write code
        that works with both Frequency and Period objects
        """
    def period(self) -> Period:
        """
        converts the Frequency to the corresponding Period
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

class Period:
    @overload
    def __init__(self, val: int | float):
        """
        create a new Period object with a given duration in seconds

        note: Period also provides classmethods to create
        an object with a duration specified in pico/nano/micro or milliseconds

        alternatively std.ps, std.ns, std.us, std.ms can be used
        """
    @overload
    def __init__(self, val: Frequency):
        """
        create a new Period object with a duration
        corresponding to the given frequency
        """
    @overload
    def __init__(self, val: Period):
        """
        create a new Period object with the same duration
        as the given value
        """
    def frequency(self) -> Frequency:
        """
        converts the Period to the corresponding frequency
        """
    def period(self) -> Period:
        """
        returns self

        this method exists to make it easier to write code
        that works with both Frequency and Period objects
        """
    @overload
    def picoseconds(self: Period) -> float:
        """
        returns the number of picoseconds in the Period
        """
    @overload
    @staticmethod
    def picoseconds(val: int | float) -> Period:
        """
        construct a Period that lasts the given
        number of picoseconds
        """
    @overload
    def nanoseconds(self: Period) -> float:
        """
        returns the number of nanoseconds in the Period
        """
    @overload
    @staticmethod
    def nanoseconds(val: int | float) -> Period:
        """
        construct a Period that lasts the given
        number of nanoseconds
        """
    @overload
    def microseconds(self: Period) -> float:
        """
        returns the number of microseconds in the Period
        """
    @overload
    @staticmethod
    def microseconds(val: int | float) -> Period:
        """
        construct a Period that lasts the given
        number of microseconds
        """
    @overload
    def milliseconds(self: Period) -> float:
        """
        returns the number of milliseconds in the Period
        """
    @overload
    @staticmethod
    def milliseconds(val: int | float) -> Period:
        """
        construct a Period that lasts the given
        number of milliseconds
        """
    @overload
    def seconds(self: Period) -> float:
        """
        returns the number of seconds in the Period
        """
    @overload
    @staticmethod
    def seconds(val: int | float) -> Period:
        """
        construct a Period that lasts the given
        number of seconds
        """
    def __eq__(self, other: Period) -> bool: ...
    def count_periods(
        self, subperiod: Period, *, allowed_delta=1e-9, float_result: bool = False
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

Duration = Period

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
        active_edge: ClockEdge = ClockEdge.RISING,
        frequency: Frequency | int | None = None,
        period: Period | int | None = None,
        duty: float = 0.5,
        phase: float = 0.0,
    ): ...
    def is_rising_edge(self) -> bool: ...
    def is_falling_edge(self) -> bool: ...
    def edge(self) -> ClockEdge: ...
    def signal(self) -> cohdl.Signal[cohdl.Bit]: ...
    def frequency(self) -> Frequency: ...
    def period(self) -> Period: ...
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
    capture_lazy: bool = False,
    comment=None,
    attributes: dict | None = None,
): ...
def sequential(
    trigger,
    reset=None,
    capture_lazy: bool = False,
    comment=None,
    attributes: dict | None = None,
): ...
