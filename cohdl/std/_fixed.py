from __future__ import annotations

from cohdl import (
    BitVector,
    Signed,
    Unsigned,
    TypeQualifier,
    Null,
    Full,
    pyeval,
    AssignMode,
    static_assert,
)

from ._core_utility import Value, instance_check, choose_first

from ._assignable_type import AssignableType
from ._template import Template


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
    @pyeval
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
    @pyeval
    def __init__(self, obj=None):
        self._obj = obj

    @pyeval
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

    @pyeval
    def __getitem__(self, arg: slice) -> _FixedResize[T]:
        assert isinstance(arg, slice)
        assert arg.step is None, "slice step may not be used"
        return _FixedResize(self._obj, arg.start, arg.stop)


#
#


class _FixedTemplateArg:
    width: int
    exp: int

    def __init__(self, arg: slice):
        assert arg.step is None, "slice step may not be used"
        assert isinstance(arg.start, int), "slice start must be an integer"
        assert isinstance(arg.stop, int), "slice stop must be an integer"
        assert arg.start >= arg.stop, "slice start must be larger tan slice stop"

        self.arg = arg
        self.width: int = arg.start - arg.stop + 1
        self.exp: int = arg.stop

    def __hash__(self):
        return hash((self.width, self.exp))

    def __eq__(self, other):
        return self.arg == other.arg

    def __repr__(self):
        return f"[{self.arg.start}:{self.arg.stop}]"


class SFixed(Template[_FixedTemplateArg], AssignableType):
    _width: _FixedTemplateArg.width
    _exp: _FixedTemplateArg.exp

    @classmethod
    @pyeval
    def _count_bits_(cls):
        return cls._width

    @classmethod
    def _from_bits_(cls, bits: BitVector, qualifier=Value):
        return cls(raw=bits.signed, _qualifier_=qualifier)

    def _to_bits_(self):
        return Value(self._val.bitvector)

    @classmethod
    @pyeval
    def min(cls):
        return -((2 ** (cls._width - 1)) * 2**cls._exp)

    @classmethod
    @pyeval
    def max(cls):
        return (2 ** (cls._width - 1) - 1) * 2**cls._exp

    @classmethod
    @pyeval
    def _adjust_val(cls, val):
        return int(val / 2**cls._exp)

    @pyeval
    def __repr__(self):
        val = TypeQualifier.decay(self._val).to_int() * 2**self._exp
        return f"{type(self)}({val})"

    @classmethod
    @pyeval
    def right(cls):
        return cls._exp

    @classmethod
    @pyeval
    def left(cls):
        return cls._exp + cls._width - 1

    def __init__(self, val=None, *, raw=None, _qualifier_=Value):
        raw_type = Signed[self._width]

        if raw is not None:
            assert val is None, "val and raw cannot be set at the same time"
            assert instance_check(raw, raw_type), "raw type must match underlying type"
            self._val: Signed = _qualifier_(raw)
        else:
            if val is None or val is Full or val is Null:
                self._val = _qualifier_[raw_type](val)
            elif isinstance(val, (int, float)):
                static_assert(
                    self.min() <= val <= self.max(),
                    "value outside valid range of fixed point number",
                )
                self._val = _qualifier_[raw_type](self._adjust_val(val))
            elif instance_check(val, Signed):
                zeros = -self._exp
                static_assert(zeros >= 0)

                self._val = _qualifier_(raw_type, val.resize(self._width, zeros=zeros))
            elif instance_check(val, Unsigned):
                zeros = -self._exp
                static_assert(zeros >= 0)
                self._val = _qualifier_[raw_type](
                    val.resize(self._width - 1, zeros=zeros)
                )
            elif instance_check(val, SFixed):
                if self.left() == val.left() and self.right() == val.right():
                    self._val = _qualifier_[raw_type](val._val)
                else:
                    assert self.left() >= val.left()
                    assert self.right() <= val.right()

                    zeros = self.right() - val.right()

                    self._val = _qualifier_[raw_type](
                        val._val.resize(self._width, zeros=zeros)
                    )
            else:
                raise AssertionError("invalid arg")

    #
    #
    #

    def _assign_(self, source, mode: AssignMode) -> None:
        if isinstance(source, SFixed):
            assert (
                source._width == self._width and source._exp == self._exp
            ), "source type ({}) does not match target type ({})".format(
                type(source), type(self)
            )

            self._val._assign_(source._val, mode)
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

        target_right = min(self.right(), other.right())
        target_left = max(self.left(), other.left()) + 1
        target_width = target_left - target_right + 1

        lhs_zeros = self.right() - target_right
        rhs_zeros = other.right() - target_right

        return SFixed[target_left:target_right](
            raw=self._val.resize(target_width, zeros=lhs_zeros)
            + other._val.resize(target_width, zeros=rhs_zeros)
        )

    def __sub__(self, other: SFixed):
        assert isinstance(other, SFixed)

        target_right = min(self.right(), other.right())
        target_left = max(self.left(), other.left()) + 1
        target_width = target_left - target_right + 1

        lhs_zeros = self.right() - target_right
        rhs_zeros = other.right() - target_right

        return SFixed[target_left:target_right](
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
            return type(self)(raw=Value(self._val))

        Result = SFixed[left:right]

        if selfleft > left:
            overflow = selfleft - left

            if overflow_style is FixedOverflowStyle.WRAP:
                if selfright >= right:
                    zeros = selfright - right

                    if overflow >= self._val.width:
                        return Result(raw=Signed[Result._width](Null))
                    else:
                        return Result(
                            raw=self._val.lsb(rest=overflow).signed.resize(zeros=zeros)
                        )
                else:
                    cutoff = right - selfright

                    if round_style is FixedRoundStyle.TRUNCATE:
                        return Result(
                            raw=Value[Signed[Result._width]](
                                self._val.lsb(rest=overflow).msb(rest=cutoff).signed
                            )
                        )
                    else:
                        assert (
                            round_style is FixedRoundStyle.ROUND
                        ), "invalid round_style {}".format(round_style)

                        if cutoff == 1:
                            do_round = (
                                Signed[2](1)
                                if self._val[cutoff - 1] and self._val[cutoff]
                                else Signed[2](0)
                            )
                        else:
                            do_round = (
                                Signed[2](1)
                                if self._val[cutoff - 1]
                                and (self._val[cutoff] or self._val[cutoff - 2 : 0])
                                else Signed[2](0)
                            )

                        return Result(
                            raw=Value[Signed[Result._width]](
                                self._val.lsb(rest=overflow).msb(rest=cutoff).signed
                                + do_round
                            )
                        )
            else:
                assert (
                    overflow_style is FixedOverflowStyle.SATURATE
                ), "invalid overflow_style {}".format(overflow_style)
                sign_bit = self._val.msb()

                overflow_bitcnt = min(selfleft - left, self._width - 1)
                overflow_bits = self._val.lsb(rest=1).msb(overflow_bitcnt)

                does_overflow = not sign_bit and overflow_bits
                does_underflow = sign_bit and ~overflow_bits

                if selfright >= right:
                    zeros = selfright - right

                    if self._val.width <= overflow:
                        default_bits = Signed[Result._width](0)
                    else:
                        default_bits = self._val.lsb(rest=overflow).signed.resize(
                            Result._width, zeros=zeros
                        )

                    return Result(
                        raw=Value[Signed[Result._width]](
                            choose_first(
                                (does_underflow, Signed[Result._width].min()),
                                (does_overflow, Signed[Result._width].max()),
                                default=default_bits,
                            )
                        )
                    )
                else:
                    cutoff = right - selfright

                    if round_style is FixedRoundStyle.TRUNCATE:
                        return Result(
                            raw=Value[Signed[Result._width]](
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
                        assert (
                            round_style is FixedRoundStyle.ROUND
                        ), "invalid round_style {}".format(round_style)

                        if cutoff == 1:
                            do_round = (
                                Signed[2](1)
                                if self._val[cutoff - 1] and self._val[cutoff]
                                else Signed[2](0)
                            )
                        else:
                            do_round = (
                                Signed[2](1)
                                if self._val[cutoff - 1]
                                and (self._val[cutoff] or self._val[cutoff - 2 : 0])
                                else Signed[2](0)
                            )

                        selected_bits = self._val.lsb(rest=overflow + 1).msb(
                            rest=cutoff
                        )
                        overflow_or_full = does_overflow or not ~selected_bits

                        return Result(
                            raw=Value[Signed[Result._width]](
                                choose_first(
                                    (does_underflow, Signed[Result._width].min()),
                                    (overflow_or_full, Signed[Result._width].max()),
                                    default=self._val.lsb(rest=overflow)
                                    .msb(rest=cutoff)
                                    .signed
                                    + do_round,
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
                        raw=Value[Signed[Result._width]](
                            self._val.msb(rest=cutoff).signed.resize(Result._width)
                        )
                    )
                else:
                    assert (
                        round_style is FixedRoundStyle.ROUND
                    ), "invalid round_style {}".format(round_style)

                    if cutoff == 1:
                        do_round = (
                            Signed[2](1)
                            if self._val[cutoff - 1] and self._val[cutoff]
                            else Signed[2](0)
                        )
                    else:
                        do_round = (
                            Signed[2](1)
                            if self._val[cutoff - 1]
                            and (self._val[cutoff] or self._val[cutoff - 2 : 0])
                            else Signed[2](0)
                        )

                    return Result(
                        raw=Value[Signed[Result._width]](
                            self._val.msb(rest=cutoff).signed.resize(Result._width)
                            + do_round
                        )
                    )


#
#


class UFixed(Template[_FixedTemplateArg], AssignableType):
    _width: _FixedTemplateArg.width
    _exp: _FixedTemplateArg.exp

    @classmethod
    @pyeval
    def _count_bits_(cls):
        return cls._width

    @classmethod
    def _from_bits_(cls, bits: BitVector, qualifier=Value):
        return cls(raw=bits.unsigned, _qualifier_=qualifier)

    def _to_bits_(self):
        return Value(self._val.bitvector)

    @classmethod
    @pyeval
    def min(cls):
        return 0

    @classmethod
    @pyeval
    def max(cls):
        return (2 ** (cls._width) - 1) * 2**cls._exp

    @classmethod
    @pyeval
    def _adjust_val(cls, val):
        return int(val / 2**cls._exp)

    @pyeval
    def __repr__(self):
        val = TypeQualifier.decay(self._val).to_int() * 2**self._exp
        return f"{type(self)}({val})"

    @classmethod
    @pyeval
    def right(cls):
        return cls._exp

    @classmethod
    @pyeval
    def left(cls):
        return cls._exp + cls._width - 1

    def __init__(self, val=None, *, raw=None, _qualifier_=Value):
        raw_type = Unsigned[self._width]

        if raw is not None:
            assert val is None, "val and raw cannot be set at the same time"
            assert instance_check(raw, raw_type), "raw type must match underlying type"
            self._val = _qualifier_(raw)
        else:
            if val is None or val is Full or val is Null:
                self._val = _qualifier_[raw_type](val)
            elif isinstance(val, (int, float)):
                static_assert(
                    self.min() <= val <= self.max(),
                    "value outside valid range of fixed point number",
                )
                self._val = _qualifier_[raw_type](self._adjust_val(val))
            elif instance_check(val, Unsigned):
                zeros = -self._exp
                static_assert(zeros >= 0)

                self._val = _qualifier_[raw_type](val.resize(self._width, zeros=zeros))
            elif instance_check(val, UFixed):
                if self.left() == val.left() and self.right() == val.right():
                    self._val = _qualifier_[raw_type](val._val)
                else:
                    assert self.left() >= val.left()
                    assert self.right() <= val.right()

                    zeros = self.right() - val.right()

                    self._val = _qualifier_[raw_type](
                        val._val.resize(self._width, zeros=zeros)
                    )
            else:
                raise AssertionError("invalid arg")

    #
    #
    #

    def _assign_(self, source, mode: AssignMode) -> None:
        if isinstance(source, UFixed):
            assert (
                source._width == self._width and source._exp == self._exp
            ), "source type ({}) does not match target type ({})".format(
                type(source), type(self)
            )
            self._val._assign_(source._val, mode)
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
        return type(self)(raw=Value(self._val))

    def __add__(self, other: UFixed):
        assert isinstance(other, UFixed)

        target_right = min(self.right(), other.right())
        target_left = max(self.left(), other.left()) + 1
        target_width = target_left - target_right + 1

        lhs_zeros = self.right() - target_right
        rhs_zeros = other.right() - target_right

        return UFixed[target_left:target_right](
            raw=self._val.resize(target_width, zeros=lhs_zeros)
            + other._val.resize(target_width, zeros=rhs_zeros)
        )

    def __sub__(self, other: UFixed):
        assert isinstance(other, UFixed)

        target_right = min(self.right(), other.right())
        target_left = max(self.left(), other.left()) + 1
        target_width = target_left - target_right + 1

        lhs_zeros = self.right() - target_right
        rhs_zeros = other.right() - target_right

        return UFixed[target_left:target_right](
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
            return type(self)(raw=Value(self._val))

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
                            raw=Value[Unsigned[Result._width]](
                                self._val.lsb(rest=overflow).msb(rest=cutoff).unsigned
                            )
                        )
                    else:
                        assert (
                            round_style is FixedRoundStyle.ROUND
                        ), "invalid round_style {}".format(round_style)

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
                            raw=Value[Unsigned[Result._width]](
                                self._val.lsb(rest=overflow).msb(rest=cutoff).unsigned
                                + do_round
                            )
                        )
            else:
                assert (
                    overflow_style is FixedOverflowStyle.SATURATE
                ), "invalid overflow_style {}".format(overflow_style)
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
                        raw=Value[Unsigned[Result._width]](
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
                            raw=Value[Unsigned[Result._width]](
                                choose_first(
                                    (does_overflow, Unsigned[Result._width].max()),
                                    default=self._val.lsb(rest=overflow)
                                    .msb(rest=cutoff)
                                    .unsigned,
                                )
                            )
                        )
                    else:
                        assert (
                            round_style is FixedRoundStyle.ROUND
                        ), "invalid round_style {}".format(round_style)

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
                            raw=Value[Unsigned[Result._width]](
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
                        raw=Value[Unsigned[Result._width]](
                            self._val.msb(rest=cutoff).unsigned.resize(Result._width)
                        )
                    )
                else:
                    assert (
                        round_style is FixedRoundStyle.ROUND
                    ), "invalid round_style {}".format(round_style)

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
                        raw=Value[Unsigned[Result._width]](
                            self._val.msb(rest=cutoff).unsigned.resize(Result._width)
                            + do_round
                        )
                    )
