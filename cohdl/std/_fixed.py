from __future__ import annotations

from cohdl import (
    Bit,
    BitVector,
    Signed,
    Unsigned,
    Signal,
    TypeQualifier,
    Null,
    Full,
    consteval,
    AssignMode,
    evaluated,
    static_assert,
)

from .utility import tc, instance_check, choose_first
from ._assignable_type import AssignableType


from typing import Type, TypeVar

import enum

import typing

T = typing.TypeVar("T")


#
#
#


class FixedRoundStyle(enum.Enum):
    ROUND = enum.auto()
    TRUNCATE = enum.auto()


class FixedOverflowStyle(enum.Enum):
    SATURATE = enum.auto()
    WRAP = enum.auto()


#
#


class _FixedResize(typing.Generic[T]):
    @consteval
    def __init__(self, obj, left, right):
        self._obj = obj
        self.left = left
        self.right = right

    def __call__(
        self,
        round_style: FixedRoundStyle = FixedRoundStyle.TRUNCATE,
        overflow_style: FixedRoundStyle = FixedOverflowStyle.WRAP,
    ) -> T:
        return self._obj.resize_fn(
            self.left,
            self.right,
            round_style=round_style,
            overflow_style=overflow_style,
        )


class _Resize(typing.Generic[T]):
    @consteval
    def __init__(self, obj=None):
        self._obj = obj

    @consteval
    def __get__(self, obj, objtype=None):
        return _Resize(obj)

    def __call__(
        self,
        left: int,
        right: int,
        round_style: FixedRoundStyle = FixedRoundStyle.TRUNCATE,
        overflow_style: FixedRoundStyle = FixedOverflowStyle.WRAP,
    ) -> T:
        return self._obj.resize_fn(
            left, right, round_style=round_style, overflow_style=overflow_style
        )

    @consteval
    def __getitem__(self, arg: slice) -> _FixedResize[T]:
        assert isinstance(arg, slice)
        assert arg.step is None
        return _FixedResize(self._obj, arg.start, arg.stop)


#
#


class SFixed(AssignableType):
    _type_map: dict[tuple[int, int], type] = dict()
    _width: int
    _exp: int

    @classmethod
    @consteval
    def min(cls):
        return -((2 ** (cls._width - 1)) * 2**cls._exp)

    @classmethod
    @consteval
    def max(cls):
        return (2 ** (cls._width - 1) - 1) * 2**cls._exp

    @classmethod
    @consteval
    def _adjust_val(cls, val):
        return int(val / 2**cls._exp)

    @classmethod
    @consteval
    def _class_repr_(cls):
        return f"SFixed[{cls._exp+cls._width-1}:{cls._exp}]"

    @consteval
    def __repr__(self):
        val = TypeQualifier.decay(self._val).to_int() * 2**self._exp
        return f"{type(self)}({val})"

    @classmethod
    @consteval
    def right(cls):
        return cls._exp

    @classmethod
    @consteval
    def left(cls):
        return cls._exp + cls._width - 1

    @consteval
    def __class_getitem__(cls, arg):
        assert cls is SFixed
        assert isinstance(arg, slice)
        assert arg.step is None
        assert arg.start > arg.stop

        width = arg.start - arg.stop + 1
        exp = arg.stop

        type_info = (width, exp)

        if type_info not in SFixed._type_map:

            class _SFixed(SFixed):
                _width = width
                _exp = exp

            SFixed._type_map[type_info] = _SFixed

        return SFixed._type_map[type_info]

    def __init__(self, val=None, *, raw=None):
        if raw is not None:
            assert val is None
            assert instance_check(raw, Signed[self._width])
            self._val: Signed = raw
        else:
            if val is None or val is Full or val is Null:
                self._val = Signed[self._width](val)
            elif isinstance(val, (int, float)):
                static_assert(
                    self.min() <= val <= self.max(),
                    "value outside valid range of fixed point number",
                )
                self._val = Signed[self._width](self._adjust_val(val))
            elif instance_check(val, Signed):
                zeros = -self._exp
                static_assert(zeros >= 0)
                self._val = tc[Signed[self._width]](
                    val.resize(self._width, zeros=zeros)
                )
            elif instance_check(val, Unsigned):
                zeros = -self._exp
                static_assert(zeros >= 0)
                self._val = tc[Signed[self._width]](
                    val.resize(self._width - 1, zeros=zeros)
                )
            else:
                raise AssertionError("invalid arg")

    #
    #
    #

    @classmethod
    def _init_qualified_(cls, Qualifier, val: SFixed | Signed | Unsigned | int):
        if isinstance(val, SFixed):
            assert cls.left() >= val.left()
            assert cls.right() <= val.right()

            zeros = cls.right() - val.right()
            return cls(raw=Qualifier(val._val.resize(cls._width, zeros=zeros)))
        elif isinstance(val, int):
            return cls(raw=Qualifier(Signed[cls._width](cls._adjust_val(val))))
        else:
            raise AssertionError("not implemented")

    def _assign_(self, source, mode: AssignMode) -> None:
        if isinstance(source, SFixed):
            if source._width == self._width and source._exp == self._exp:
                self._val._assign_(source._val, mode)
            else:
                raise AssertionError("invalid")
        else:
            self._assign_(type(self)(source), mode)

    #
    #

    def __eq__(self, other: int | float | SFixed):
        if isinstance(other, (int, float)):
            return type(self)(other) == self
        else:
            assert isinstance(other, SFixed)
            assert type(other) is type(self)

            return self._val == other._val

    #
    #

    def __bool__(self):
        return bool(self._val)

    def __abs__(self):
        return type(self)(raw=abs(self._val))

    def __add__(self, other: SFixed):
        assert isinstance(other, SFixed)

        target_rigth = min(self.right(), other.right())
        target_left = max(self.left(), other.left()) + 1
        target_width = target_left - target_rigth + 1

        lhs_zeros = self.right() - target_rigth
        rhs_zeros = other.right() - target_rigth

        return SFixed[target_left:target_rigth](
            raw=self._val.resize(target_width, zeros=lhs_zeros)
            + other._val.resize(target_width, zeros=rhs_zeros)
        )

    def __sub__(self, other: SFixed):
        assert isinstance(other, SFixed)

        target_rigth = min(self.right(), other.right())
        target_left = max(self.left(), other.left()) + 1
        target_width = target_left - target_rigth + 1

        lhs_zeros = self.right() - target_rigth
        rhs_zeros = other.right() - target_rigth

        return SFixed[target_left:target_rigth](
            raw=self._val.resize(target_width, zeros=lhs_zeros)
            - other._val.resize(target_width, zeros=rhs_zeros)
        )

    def __mul__(self, other: SFixed):
        assert isinstance(other, SFixed)

        return SFixed[self.left() + other.left() + 1 : self.right() + other.right()](
            raw=self._val * other._val
        )

    resize = _Resize()

    def resize_fn(
        self,
        left: int,
        right: int,
        round_style: FixedRoundStyle = FixedRoundStyle.TRUNCATE,
        overflow_style: FixedRoundStyle = FixedOverflowStyle.WRAP,
    ):
        selfleft = self.left()
        selfright = self.right()

        if selfleft == left and selfright == right:
            return type(self)(raw=tc(self._val))

        Result = SFixed[left:right]

        if selfleft > left:
            overflow = selfleft - left

            if overflow_style is FixedOverflowStyle.WRAP:
                if selfright >= right:
                    zeros = selfright - right
                    return Result(
                        raw=self._val.lsb(rest=overflow).signed.resize(zeros=zeros)
                    )
                else:
                    cutoff = right - selfright

                    if round_style is FixedRoundStyle.TRUNCATE:
                        return Result(
                            raw=tc[Signed[Result._width]](
                                self._val.lsb(rest=overflow).msb(rest=cutoff).signed
                            )
                        )
                    else:
                        assert round_style is FixedRoundStyle.ROUND
                        return Result(
                            raw=tc[Signed[Result._width]](
                                self._val.lsb(rest=overflow).msb(rest=cutoff).signed
                                + self._val[cutoff - 1 : cutoff - 1]
                                .unsigned.resize(Result._width)
                                .signed
                            )
                        )
            else:
                assert overflow_style is FixedOverflowStyle.SATURATE
                overflow_bits = self._val.msb(selfleft - left)

                does_underflow = bool(overflow_bits.msb())
                does_overflow = bool(overflow_bits)

                if selfright >= right:
                    zeros = selfright - right
                    return Result(
                        raw=tc[Signed[Result._width]](
                            choose_first(
                                (does_underflow, Signed[Result._width].min()),
                                (does_overflow, Signed[Result._width].max()),
                                default=self._val.lsb(rest=overflow).signed.resize(
                                    Result._width, zeros=zeros
                                ),
                            )
                        )
                    )
                else:
                    cutoff = right - selfright

                    if round_style is FixedRoundStyle.TRUNCATE:
                        return Result(
                            raw=tc[Signed[Result._width]](
                                choose_first(
                                    (does_underflow, Signed[Result._width].min()),
                                    (does_overflow, Signed[Result._width].max()),
                                    default=self._val.lsb(rest=overflow)
                                    .msb(rest=cutoff)
                                    .signed,
                                )
                            )
                        )
                    else:
                        assert round_style is FixedRoundStyle.ROUND

                        return Result(
                            raw=tc[Signed[Result._width]](
                                choose_first(
                                    (does_underflow, Signed[Result._width].min()),
                                    (does_overflow, Signed[Result._width].max()),
                                    default=self._val.lsb(rest=overflow)
                                    .msb(rest=cutoff)
                                    .signed
                                    + self._val[cutoff - 1 : cutoff - 1]
                                    .unsigned.resize(Result._width)
                                    .signed,
                                )
                            )
                        )

        else:
            if selfright >= right:
                return Result(
                    raw=self._val.resize(Result._width, zeros=selfright - right)
                )
            else:
                cutoff = right - selfright

                if round_style is FixedRoundStyle.TRUNCATE:
                    return Result(
                        raw=tc[Signed[Result._width]](
                            self._val.msb(rest=cutoff).signed.resize(Result._width)
                        )
                    )
                else:
                    assert round_style is FixedRoundStyle.ROUND

                    return Result(
                        raw=tc[Signed[Result._width]](
                            self._val.msb(rest=cutoff).signed.resize(Result._width)
                            + self._val[cutoff - 1 : cutoff - 1]
                            .unsigned.resize(Result._width)
                            .signed,
                        )
                    )


#
#


class UFixed(AssignableType):
    _type_map: dict[tuple[int, int], type] = dict()
    _width: int
    _exp: int

    @classmethod
    @consteval
    def min(cls):
        return 0

    @classmethod
    @consteval
    def max(cls):
        return (2 ** (cls._width) - 1) * 2**cls._exp

    @classmethod
    @consteval
    def _adjust_val(cls, val):
        return int(val / 2**cls._exp)

    @classmethod
    @consteval
    def _class_repr_(cls):
        return f"UFixed[{cls._exp+cls._width-1}:{cls._exp}]"

    @consteval
    def __repr__(self):
        val = TypeQualifier.decay(self._val).to_int() * 2**self._exp
        return f"{type(self)}({val})"

    @classmethod
    @consteval
    def right(cls):
        return cls._exp

    @classmethod
    @consteval
    def left(cls):
        return cls._exp + cls._width - 1

    @consteval
    def __class_getitem__(cls, arg):
        assert cls is UFixed
        assert isinstance(arg, slice)
        assert arg.step is None
        assert arg.start >= arg.stop

        width = arg.start - arg.stop + 1
        exp = arg.stop

        type_info = (width, exp)

        if type_info not in UFixed._type_map:

            class _UFixed(UFixed):
                _width = width
                _exp = exp

            UFixed._type_map[type_info] = _UFixed

        return UFixed._type_map[type_info]

    def __init__(self, val=None, *, raw=None):
        if raw is not None:
            assert val is None
            assert instance_check(raw, Unsigned[self._width])
            self._val: Unsigned = raw

        else:
            if val is None or val is Full or val is Null:
                self._val = Unsigned[self._width](val)
            elif isinstance(val, (int, float)):
                static_assert(
                    self.min() <= val <= self.max(),
                    "value outside valid range of fixed point number",
                )
                self._val = Unsigned[self._width](self._adjust_val(val))
            elif instance_check(val, Unsigned):
                zeros = -self._exp
                static_assert(zeros >= 0)
                self._val = tc[Unsigned[self._width]](
                    val.resize(self._width, zeros=zeros)
                )
            else:
                raise AssertionError("invalid arg")

    #
    #
    #

    @classmethod
    def _init_qualified_(cls, Qualifier, val: UFixed | Unsigned | int | None = None):
        if isinstance(val, UFixed):
            assert cls.left() >= val.left()
            assert cls.right() <= val.right()

            zeros = cls.right() - val.right()
            return cls(raw=Qualifier(val._val.resize(cls._width, zeros=zeros)))
        elif isinstance(val, int):
            return cls(raw=Qualifier(Unsigned[cls._width](cls._adjust_val(val))))
        elif val is None:
            return cls(raw=Qualifier(Unsigned[cls._width]()))
        else:
            raise AssertionError("not implemented")

    def _assign_(self, source, mode: AssignMode) -> None:
        if isinstance(source, UFixed):
            if source._width == self._width and source._exp == self._exp:
                self._val._assign_(source._val, mode)
            else:
                raise AssertionError("invalid")
        else:
            self._assign_(type(self)(source), mode)

    #
    #

    def __eq__(self, other: int | float | UFixed):
        if isinstance(other, (int, float)):
            return type(self)(other) == self
        else:
            assert isinstance(other, UFixed)
            assert type(other) is type(self)

            return self._val == other._val

    #
    #

    def __bool__(self):
        return bool(self._val)

    def __abs__(self):
        return type(self)(raw=tc(self._val))

    def __add__(self, other: UFixed):
        assert isinstance(other, UFixed)

        target_rigth = min(self.right(), other.right())
        target_left = max(self.left(), other.left()) + 1
        target_width = target_left - target_rigth + 1

        lhs_zeros = self.right() - target_rigth
        rhs_zeros = other.right() - target_rigth

        return UFixed[target_left:target_rigth](
            raw=self._val.resize(target_width, zeros=lhs_zeros)
            + other._val.resize(target_width, zeros=rhs_zeros)
        )

    def __sub__(self, other: UFixed):
        assert isinstance(other, UFixed)

        target_rigth = min(self.right(), other.right())
        target_left = max(self.left(), other.left()) + 1
        target_width = target_left - target_rigth + 1

        lhs_zeros = self.right() - target_rigth
        rhs_zeros = other.right() - target_rigth

        return UFixed[target_left:target_rigth](
            raw=self._val.resize(target_width, zeros=lhs_zeros)
            - other._val.resize(target_width, zeros=rhs_zeros)
        )

    def __mul__(self, other: UFixed):
        assert isinstance(other, UFixed)

        return UFixed[self.left() + other.left() + 1 : self.right() + other.right()](
            raw=self._val * other._val
        )

    resize = _Resize()

    def resize_fn(
        self,
        left: int,
        right: int,
        round_style: FixedRoundStyle = FixedRoundStyle.TRUNCATE,
        overflow_style: FixedRoundStyle = FixedOverflowStyle.WRAP,
    ):
        selfleft = self.left()
        selfright = self.right()

        if selfleft == left and selfright == right:
            return type(self)(raw=tc(self._val))

        Result = UFixed[left:right]

        if selfleft > left:
            overflow = selfleft - left

            if overflow_style is FixedOverflowStyle.WRAP:
                if selfright >= right:
                    zeros = selfright - right

                    if overflow >= self._val.width:
                        return Result(raw=Unsigned[Result._width](Null))
                    else:
                        return Result(
                            raw=self._val.lsb(rest=overflow).unsigned.resize(
                                zeros=zeros
                            )
                        )
                else:
                    cutoff = right - selfright

                    if round_style is FixedRoundStyle.TRUNCATE:
                        return Result(
                            raw=tc[Unsigned[Result._width]](
                                self._val.lsb(rest=overflow).msb(rest=cutoff).unsigned
                            )
                        )
                    else:
                        assert round_style is FixedRoundStyle.ROUND

                        if cutoff == 1:
                            do_round = (
                                Unsigned[1](1)
                                if self._val[cutoff - 1] and self._val[cutoff]
                                else Unsigned[1](0)
                            )
                        else:
                            do_round = (
                                Unsigned[1](1)
                                if self._val[cutoff - 1]
                                and (self._val[cutoff] or self._val[cutoff - 2 : 0])
                                else Unsigned[1](0)
                            )

                        return Result(
                            raw=tc[Unsigned[Result._width]](
                                self._val.lsb(rest=overflow).msb(rest=cutoff).unsigned
                                + do_round
                            )
                        )
            else:
                assert overflow_style is FixedOverflowStyle.SATURATE
                overflow_bits = self._val.msb(selfleft - left)

                does_overflow = bool(overflow_bits)

                if selfright >= right:
                    zeros = selfright - right

                    if self._val.width <= overflow:
                        default_bits = Unsigned[Result._width](0)
                    else:
                        default_bits = self._val.lsb(rest=overflow).unsigned.resize(
                            Result._width, zeros=zeros
                        )

                    return Result(
                        raw=tc[Unsigned[Result._width]](
                            choose_first(
                                (does_overflow, Unsigned[Result._width].max()),
                                default=default_bits,
                            )
                        )
                    )
                else:
                    cutoff = right - selfright

                    if round_style is FixedRoundStyle.TRUNCATE:
                        return Result(
                            raw=tc[Unsigned[Result._width]](
                                choose_first(
                                    (does_overflow, Unsigned[Result._width].max()),
                                    default=self._val.lsb(rest=overflow)
                                    .msb(rest=cutoff)
                                    .unsigned,
                                )
                            )
                        )
                    else:
                        assert round_style is FixedRoundStyle.ROUND

                        if cutoff == 1:
                            do_round = (
                                Unsigned[1](1)
                                if self._val[cutoff - 1] and self._val[cutoff]
                                else Unsigned[1](0)
                            )
                        else:
                            do_round = (
                                Unsigned[1](1)
                                if self._val[cutoff - 1]
                                and (self._val[cutoff] or self._val[cutoff - 2 : 0])
                                else Unsigned[1](0)
                            )

                        selected_bits = self._val.lsb(rest=overflow).msb(rest=cutoff)
                        overflow_or_full = does_overflow or not ~selected_bits

                        return Result(
                            raw=tc[Unsigned[Result._width]](
                                choose_first(
                                    (overflow_or_full, Unsigned[Result._width].max()),
                                    default=selected_bits.unsigned + do_round,
                                )
                            )
                        )

        else:
            if selfright >= right:
                return Result(
                    raw=self._val.resize(Result._width, zeros=selfright - right)
                )
            else:
                cutoff = right - selfright

                if round_style is FixedRoundStyle.TRUNCATE:
                    return Result(
                        raw=tc[Unsigned[Result._width]](
                            self._val.msb(rest=cutoff).unsigned.resize(Result._width)
                        )
                    )
                else:
                    assert round_style is FixedRoundStyle.ROUND

                    if cutoff == 1:
                        do_round = (
                            Unsigned[1](1)
                            if self._val[cutoff - 1] and self._val[cutoff]
                            else Unsigned[1](0)
                        )
                    else:
                        do_round = (
                            Unsigned[1](1)
                            if self._val[cutoff - 1]
                            and (self._val[cutoff] or self._val[cutoff - 2 : 0])
                            else Unsigned[1](0)
                        )

                    return Result(
                        raw=tc[Unsigned[Result._width]](
                            self._val.msb(rest=cutoff).unsigned.resize(Result._width)
                            + do_round
                        )
                    )
