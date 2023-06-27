from __future__ import annotations

import inspect
import typing

from cohdl._core._type_qualifier import (
    TypeQualifierBase,
    TypeQualifier,
    Temporary,
    Signal,
)
from cohdl._core import Bit, BitVector, Unsigned, select_with, evaluated, true, Null
from cohdl._core._intrinsic import _intrinsic

from ._context import Duration, Context


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


#
#
#


class _UncheckedType:
    pass


def _check_type(result, expected):
    if expected is _UncheckedType:
        return True
    elif expected is None:
        return result is None
    else:
        return instance_check(result, expected)


class _TypeCheckedExpression:
    def __init__(self, expected_type: type | tuple = _UncheckedType):
        self._expected = expected_type

    def _checked(self, arg):
        assert _check_type(arg, self._expected), "invalid type in checked expression"
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


def binary_fold(fn, first, *args):
    if len(args) == 0:
        return Temporary(first)
    else:
        return fn(first, binary_fold(fn, *args))


def concat(first, *args):
    return binary_fold(lambda a, b: a @ b, first, *args)


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

    async def shift_all(self, target: Bit, shift_delayed=False):
        if not shift_delayed:
            target <<= self.shift()

        while not self.empty():
            target <<= self.shift()

    def empty(self):
        if self._msb_first:
            return not self._data.msb(rest=1)
        else:
            return not self._data.lsb(rest=1)

    def shift(self):
        if self._msb_first:
            self._data <<= self._data.lsb(rest=1) @ Bit(0)
            return self._data.msb()
        else:
            self._data <<= Bit(0) @ self._data.msb(rest=1)
            return self._data.lsb()


class InShiftRegister:
    def __init__(self, len: int, msb_first=False):
        self._msb_first = msb_first
        self._len = len

        if msb_first:
            self._data = Signal(BitVector[len](Null) @ Bit(True))
        else:
            self._data = Signal(Bit(True) @ BitVector[len](Null))

    async def shift_all(self, src: Bit, shift_delayed=False):
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

    def shift(self, src: Bit):
        assert not self.full()
        if self._msb_first:
            self._data <<= self._data.lsb(rest=1) @ src
        else:
            self._data <<= src @ self._data.msb(rest=1)

    def data(self):
        if self._msb_first:
            return self._data.lsb(rest=1).copy()
        else:
            return self._data.msb(rest=1).copy()
