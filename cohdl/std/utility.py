from __future__ import annotations

import inspect
import typing

from cohdl._core._type_qualifier import (
    TypeQualifierBase,
    TypeQualifier,
    Temporary,
    Signal,
)
from cohdl._core import (
    Bit,
    BitVector,
    Unsigned,
    select_with,
    evaluated,
    true,
    Null,
    Full,
    static_assert,
    concurrent_context,
)

from cohdl._core._intrinsic import _intrinsic

from cohdl._core._intrinsic import comment as cohdl_comment

from ._context import Duration, Context


def comment(*lines):
    cohdl_comment(*lines)


class _TC:
    def __init__(self, T=None) -> None:
        self._T = T

    def __call__(self, arg):
        if self._T is None:
            if isinstance(arg, TypeQualifier):
                assert evaluated(), "expression only allowed in synthesizable contexts"
                return Temporary(arg)
            elif isinstance(arg, TypeQualifierBase):
                return TypeQualifierBase.decay(arg)
            else:
                return arg
        else:
            if isinstance(arg, TypeQualifier):
                assert evaluated(), "expression only allowed in synthesizable contexts"
                return Temporary[self._T](arg)
            elif isinstance(arg, TypeQualifierBase):
                return TypeQualifierBase.decay(arg)
            else:
                return self._T(arg)

    @_intrinsic
    def __getitem__(self, T):
        assert self._T is None, "redefining expression type not allowed"
        return _TC(T)


tc = _TC()

#
#
#


@_intrinsic
def iscouroutinefunction(fn):
    return inspect.iscoroutinefunction(fn)


def instance_check(val, type):
    return isinstance(TypeQualifierBase.decay(val), type)


def subclass_check(val, type):
    return issubclass(TypeQualifierBase.decay(val), type)


async def as_awaitable(fn, /, *args, **kwargs):
    if iscouroutinefunction(fn):
        return await fn(*args, **kwargs)
    else:
        return fn(*args, **kwargs)


#
#
#


@_intrinsic
def zeros(len: int):
    return BitVector[len](Null)


@_intrinsic
def ones(len: int):
    return BitVector[len](Full)


@_intrinsic
def width(inp: Bit | BitVector) -> int:
    if instance_check(inp, Bit):
        return 1
    else:
        return inp.width


def one_hot(width: int, bit_pos: int | Unsigned) -> BitVector:
    assert 0 <= bit_pos < width, "bit_pos out of range"
    return (Unsigned[width](1) << bit_pos).bitvector


def reverse_bits(inp: BitVector) -> BitVector:
    return concat(*inp)


#
#
#


def const_cond(arg):
    result = bool(arg)
    static_assert(isinstance(result, bool), "condition is not a constant")
    return result


class _UncheckedType:
    pass


def _check_type(result, expected):
    if expected is _UncheckedType:
        return True
    elif expected is None:
        return result is None
    else:
        return instance_check(result, expected)


@_intrinsic
def _format_type_check_error(expected_type, actual_type):
    return f"invalid type in checked expression: expected '{expected_type}' but got '{actual_type}'"


class _TypeCheckedExpression:
    def __init__(self, expected_type: type | tuple = _UncheckedType):
        self._expected = expected_type

    def _checked(self, arg):
        assert _check_type(arg, self._expected), _format_type_check_error(
            self._expected, arg
        )
        return arg

    def __getitem__(self, expected_type):
        return type(self)(expected_type)


class _CheckType(_TypeCheckedExpression):
    def __call__(self, arg):
        assert (
            self._expected is not _UncheckedType
        ), "no type specified in std.check_type"
        return self._checked(arg)


class _Select(_TypeCheckedExpression):
    def __call__(self, arg, branches: dict, default=None):
        return self._checked(
            select_with(
                arg,
                branches,
                default=default,
            )
        )


def _first_impl(*args, default):
    if len(args) == 0:
        return default
    else:
        first, *rest = args
        return first[1] if first[0] else _first_impl(*rest, default=default)


class _ChooseFirst(_TypeCheckedExpression):
    def __call__(self, *args, default):
        return self._checked(_first_impl(*args, default=default))


class _Cond(_TypeCheckedExpression):
    def __call__(self, cond: bool, on_true, on_false):
        return self._checked(on_true if cond else on_false)


check_type = _CheckType()
select = _Select()
choose_first = _ChooseFirst()
cond = _Cond()


@_intrinsic
def _get_return_type_hint(fn):
    return typing.get_type_hints(fn).get("return", _UncheckedType)


def check_return(fn):
    if iscouroutinefunction(fn):

        async def wrapper(*args, **kwargs):
            result = await fn(*args, **kwargs)
            assert _check_type(
                result, _get_return_type_hint(fn)
            ), "invalid return value in function call"
            return result

    else:

        def wrapper(*args, **kwargs):
            result = fn(*args, **kwargs)
            assert _check_type(
                result, _get_return_type_hint(fn)
            ), "invalid return value in function call"
            return result

    wrapper.__name__ = fn.__name__
    return wrapper


#
#
#


def binary_fold(fn, first, *args, right_fold=False):
    if len(args) == 0:
        return tc(first)
    else:
        if right_fold:
            return fn(first, binary_fold(fn, *args), right_fold=True)
        else:
            snd, *rest = args
            return binary_fold(fn, fn(first, snd), *rest)


def _concat_impl(first, *args):
    return binary_fold(lambda a, b: a @ b, first, *args)


def concat(first, *args):
    if len(args) == 0:
        if instance_check(first, Bit):
            return as_bitvector(first)
        else:
            assert instance_check(first, BitVector)
            return tc[BitVector[len(first)]](first)
    else:
        return _concat_impl(first, *args)


def stretch(val: Bit | BitVector, factor: int):
    if instance_check(val, Bit):
        return concat(*[val for _ in range(factor)])
    elif instance_check(val, BitVector):
        return concat(*[stretch(b, factor) for b in val])
    else:
        raise AssertionError("invalid argument")


def apply_mask(old: BitVector, new: BitVector, mask: BitVector):
    assert old.width == new.width
    return (old & ~mask) | (new & mask)


def as_bitvector(inp: Bit):
    assert instance_check(inp, Bit)
    return (inp @ inp)[0:0]


#
#
#


@_intrinsic
def max_int(arg: int | Unsigned):
    if isinstance(arg, int):
        return arg
    else:
        return TypeQualifierBase.decay(arg).max_int()


@_intrinsic
def int_log_2(inp: int) -> int:
    assert isinstance(inp, int)
    assert inp > 0
    assert inp.bit_count() == 1
    return inp.bit_length() - 1


@_intrinsic
def _is_one(val):
    x = isinstance(val, int) and val == 1
    return x


async def wait_for(duration: int | Unsigned | Duration, *, allow_zero: bool = False):
    if isinstance(duration, Duration):
        ctx = Context.current()
        assert (
            ctx is not None
        ), "wait_for can only infer the clock in sequential contexts created with std.Context"
        cnt = duration.count_periods(ctx.clk().period())
    else:
        cnt = duration

    if allow_zero:
        if duration == 0:
            return
    else:
        assert (
            cnt > 0
        ), "waiting for 0 ticks only possible when allow_zero is set to True"

    if _is_one(cnt):
        await true
    else:
        counter = Signal[Unsigned.upto(max_int(cnt - 1))](cnt - 1)
        while counter:
            counter <<= counter - 1


class OutShiftRegister:
    def __init__(self, src: BitVector, msb_first=False):
        self._msb_first = msb_first

        if msb_first:
            self._data = Signal(src @ Bit(True), name="shift_out")
        else:
            self._data = Signal(Bit(True) @ src, name="shift_out")

    def set_data(self, data):
        assert len(data) == len(self._data) - 1
        if self._msb_first:
            self._data <<= Signal(data @ Bit(True))
        else:
            self._data <<= Signal(Bit(True) @ data)

    async def shift_all(self, target: Bit | BitVector, shift_delayed=False):
        count = target.width if instance_check(target, BitVector) else None

        if not shift_delayed:
            target <<= self.shift(count)

        while not self.empty():
            target <<= self.shift(count)

    def empty(self):
        if self._msb_first:
            return not self._data.lsb(rest=1)
        else:
            return not self._data.msb(rest=1)

    def shift(self, count: int | None = None):
        shift_width = count if count is not None else 1
        assert (
            isinstance(shift_width, int) and shift_width > 0
        ), "count must be a constant positive integer value"

        if self._msb_first:
            after_shift = self._data.lsb(rest=shift_width) @ zeros(shift_width)

            # check, that the marker bit is never shifted out of the extended register
            assert bool(after_shift), "invalid shift, register already empty"
            self._data <<= after_shift
            return self._data.msb(count)
        else:
            after_shift = zeros(shift_width) @ self._data.msb(rest=shift_width)
            assert bool(after_shift), "invalid shift, register already empty"
            self._data <<= after_shift
            return self._data.lsb(count)


class InShiftRegister:
    def __init__(self, len: int, msb_first=False):
        self._msb_first = msb_first
        self._len = len

        if msb_first:
            self._data = Signal(BitVector[len](Null) @ Bit(True))
        else:
            self._data = Signal(Bit(True) @ BitVector[len](Null))

    async def shift_all(self, src: Bit | BitVector, shift_delayed=False):
        if not shift_delayed:
            self.shift(src)

        while not self.full():
            self.shift(src)

        return self.data()

    def clear(self):
        if self._msb_first:
            self._data <<= BitVector[self._len](Null) @ Bit(True)
        else:
            self._data <<= Bit(True) @ BitVector[self._len](Null)

    def full(self):
        if self._msb_first:
            return self._data.msb().copy()
        else:
            return self._data.lsb().copy()

    def shift(self, src: Bit | BitVector):
        shift_cnt = width(src)

        if self._msb_first:
            assert not self._data.msb(shift_cnt), "invalid shift, register already full"
            self._data <<= self._data.lsb(rest=shift_cnt) @ src
        else:
            assert not self._data.lsb(shift_cnt), "invalid shift, register already full"
            self._data <<= src @ self._data.msb(rest=shift_cnt)

    def data(self):
        if self._msb_first:
            return self._data.lsb(rest=1).copy()
        else:
            return self._data.msb(rest=1).copy()


def continuous_counter(ctx: Context, limit):
    counter = Signal[Unsigned.upto(max_int(limit))](0)

    @ctx
    def proc():
        nonlocal counter
        if counter >= limit:
            counter <<= 0
        else:
            counter <<= counter + 1

    return counter


class ToggleSignal:
    def __init__(
        self,
        ctx: Context,
        off_duration: int | Unsigned | Duration,
        on_duration: int | Unsigned | Duration,
        initial_on=False,
    ):
        assert isinstance(initial_on, bool)

        if isinstance(on_duration, Duration):
            cnt_switch_on = on_duration.count_periods(ctx.clk().period())
        else:
            cnt_switch_on = on_duration

        if isinstance(off_duration, Duration):
            cnt_switch_off = off_duration.count_periods(ctx.clk().period())
        else:
            cnt_switch_off = off_duration

        if isinstance(cnt_switch_on, Signal) or isinstance(cnt_switch_off, Signal):
            max_counter_end = max_int(cnt_switch_off) + max_int(cnt_switch_on) - 1
            counter_end = Signal[Unsigned.upto(max_counter_end)]()

            @concurrent_context
            def logic():
                counter_end.next = cnt_switch_off + cnt_switch_on - 1

        else:
            counter_end = cnt_switch_off + cnt_switch_on - 1

        self._reset = Signal[Bit](False)

        counter = continuous_counter(ctx.or_reset(self._reset), counter_end)

        self._state = Signal[Bit]()
        self._rising = Signal[Bit]()
        self._falling = Signal[Bit]()

        if initial_on:

            @concurrent_context
            def logic():
                self._state <<= counter < cnt_switch_on
                self._rising <<= counter == 0
                self._falling <<= counter == cnt_switch_on

        else:

            @concurrent_context
            def logic():
                self._state <<= counter >= cnt_switch_off
                self._rising <<= counter == cnt_switch_off
                self._falling <<= counter == 0

    def reset_signal(self):
        return self._reset

    def enable(self):
        self._reset <<= False

    def disable(self):
        self._reset <<= True

    def rising(self):
        return self._rising

    def falling(self):
        return self._falling

    def state(self):
        return self._state
