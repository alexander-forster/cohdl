from __future__ import annotations

import typing
from typing import overload

import enum

from cohdl._core._bit import Bit
from cohdl._core._bit_vector import BitVector
from cohdl._core._unsigned import Unsigned
from cohdl._core._signed import Signed
from cohdl._core._intrinsic_operations import AssignMode
from cohdl._core._integer import Integer

T = typing.TypeVar("T", Bit, BitVector)
U = typing.TypeVar("U", Bit, BitVector)
VEC_T = typing.TypeVar("VEC_T", BitVector)
DIR = typing.TypeVar("DIR")
Self = typing.TypeVar("Self")

class Attribute:
    name: str
    attr_type: type

    def __init__(self, value):
        self.value = value

class TypeQualifierBase(typing.Generic[T]):
    def decay(val): ...

class TypeQualifier(typing.Generic[T], TypeQualifierBase[T]):
    @property
    def type(cls): ...
    @property
    def qualifier(self): ...
    def decay(val): ...
    @property
    def width(self) -> int: ...

    #
    #
    #

    def __init__(
        self,
        value=None,
        *,
        name: str | None = None,
        attributes: dict | None = None,
        noreset: bool = False,
        maybe_uninitialized: bool = False,
    ) -> None:
        """
        Create a new type qualified object with an optional default `value`.

        `name` is only a hint. The compiler will add a counter suffix to resolve name collisions.
        `attributes` are currently unused.

        Objects declared with `noreset` will not be automatically reset in
        synthesizable contexts (the default value is still used during initialization).

        CoHDL perform some basic checks to ensure, that all locally declared objects
        are initialized before they are used. Set `maybe_uninitialized` to True to
        opt out of these checks.
        """

    def name(self) -> str: ...
    def has_default(self) -> bool: ...
    def default(self): ...
    def __len__(self) -> int: ...
    def __iter__(self): ...
    def get(self) -> T: ...
    @overload
    def __getitem__(self, arg: int) -> TypeQualifier[Bit]: ...
    @overload
    def __getitem__(self, arg: slice) -> TypeQualifier[BitVector]: ...
    @overload
    def __getitem__(self, arg: tuple | list) -> Temporary[BitVector]: ...
    @overload
    def lsb(self, count: None = None, rest: None = None) -> TypeQualifier[Bit]: ...
    @overload
    def lsb(
        self, count: None | int = None, rest: None | int = None
    ) -> TypeQualifier[BitVector]: ...
    @overload
    def msb(self, count: None = None, rest: None = None) -> TypeQualifier[Bit]: ...
    @overload
    def msb(
        self, count: None | int = None, rest: None | int = None
    ) -> TypeQualifier[BitVector]: ...
    @overload
    def left(self, count: None = None, rest: None = None) -> TypeQualifier[Bit]: ...
    @overload
    def left(
        self, count: None | int = None, rest: None | int = None
    ) -> TypeQualifier[BitVector]: ...
    @overload
    def right(self, count: None = None, rest: None = None) -> TypeQualifier[Bit]: ...
    @overload
    def right(
        self, count: None | int = None, rest: None | int = None
    ) -> TypeQualifier[BitVector]: ...

    #
    #
    #

    def __bool__(self) -> bool: ...
    def __and__(self, other) -> Temporary[T]: ...
    def __rand__(self, other) -> Temporary[T]: ...
    def __or__(self, other) -> Temporary[T]: ...
    def __ror__(self, other) -> Temporary[T]: ...
    def __xor__(self, other) -> Temporary[T]: ...
    def __rxor__(self, other) -> Temporary[T]: ...
    def __matmul__(self, other) -> Temporary[T]: ...
    def __rmatmul__(self, other) -> Temporary[T]: ...
    #
    # numeric operators
    #

    def __add__(self, other) -> Temporary[T]: ...
    def __radd__(self, other) -> Temporary[T]: ...
    def __sub__(self, other) -> Temporary[T]: ...
    def __rsub__(self, other) -> Temporary[T]: ...
    def __mul__(self, other) -> Temporary[T]: ...
    def __rmul__(self, other) -> Temporary[T]: ...
    def __floordiv__(self, other) -> Temporary[T]: ...
    def __rfloordiv__(self, other) -> Temporary[T]: ...
    def _cohdl_truncdiv_(self, other) -> Temporary[T]: ...
    def _cohdl_rtruncdiv_(self, other) -> Temporary[T]: ...
    def __mod__(self, other) -> Temporary[T]: ...
    def __rmod__(self, other) -> Temporary[T]: ...
    def _cohdl_rem_(self, other) -> Temporary[T]: ...
    def _cohdl_rrem_(self, other) -> Temporary[T]: ...

    #
    # shift operators
    #

    def __lshift__(self, rhs: Unsigned | int | Integer) -> Temporary[T]: ...
    def __rshift__(self, rhs: Unsigned | int | Integer) -> Temporary[T]: ...

    #
    # compare
    #

    def __eq__(self, other) -> bool: ...
    def __ne__(self, other) -> bool: ...
    def __lt__(self, other) -> bool: ...
    def __gt__(self, other) -> bool: ...
    def __le__(self, other) -> bool: ...
    def __ge__(self, other) -> bool: ...
    #
    # unary operators
    #

    def __inv__(self: Self) -> Temporary[T]: ...
    def __neg__(self: Self) -> Temporary[T]: ...
    def __pos__(self: Self) -> Temporary[T]: ...
    #
    # casts
    #
    @property
    def unsigned(self) -> TypeQualifier[Unsigned]: ...
    @unsigned.setter
    def unsigned(self, value: TypeQualifier[Unsigned] | Unsigned | int): ...
    @property
    def signed(self) -> TypeQualifier[Signed]: ...
    @signed.setter
    def signed(self, value: TypeQualifier[Signed] | Signed | int): ...
    @property
    def bitvector(self) -> TypeQualifier[BitVector]: ...
    @bitvector.setter
    def bitvector(self, value: TypeQualifier[BitVector] | BitVector | str): ...

    #
    # helper methods
    #

    def resize(
        self, target_width: int | None = None, *, zeros: int = 0
    ) -> Temporary[T]: ...
    def copy(self) -> Temporary[T]: ...

class Signal(typing.Generic[T], TypeQualifier[T]):
    def __init__(
        self,
        value=None,
        *,
        name: str | None = None,
        attributes: dict | None = None,
        delayed_init: bool = False,
        maybe_uninitialized: bool = False,
    ) -> None:
        """
        Create a new Signal with an optional default `value`.

        `name` is only a hint. The compiler will add a counter suffix to resolve name collisions.
        `attributes` are currently unused.

        `delayed_init` only has an effect for signals created locally in a sequential context.
        By default these initializations are *NOT* the same as a signal assignment.
        Instead initialization takes place immediately like variable assignment.
        When `delayed_init` is set to true initialization behaves like a signal assignment
        and takes one clock cycle.

        CoHDL performs some basic checks, to ensure that all locally declared objects
        are initialized before they are used. Set `maybe_uninitialized` to True to
        opt out of these checks.

        >>> @std.sequential(clk)
        >>> def example():
        >>>     a = Signal[Bit](input)
        >>>     b = Signal[Bit](a)
        >>>     c = Signal[Bit](b)
        >>>
        >>>     # this assertion always holds
        >>>     assert input == a == b == c
        >>>
        >>>     x = Signal[Bit](input, delayed_init=True)
        >>>     y = Signal[Bit](x, delayed_init=True)
        >>>
        >>>     assert x == prev(input)
        >>>     assert x == prev(prev(input))
        """
    #
    #
    #
    @overload
    def __getitem__(self, arg: int) -> Signal[Bit]: ...
    @overload
    def __getitem__(self, arg: slice) -> Signal[BitVector]: ...
    @overload
    def __getitem__(self, arg: tuple | list) -> Temporary[BitVector]: ...
    @overload
    def lsb(self, count: None = None, rest: None = None) -> Signal[Bit]: ...
    @overload
    def lsb(
        self, count: None | int = None, rest: None | int = None
    ) -> Signal[BitVector]: ...
    @overload
    def msb(self, count: None = None, rest: None = None) -> Signal[Bit]: ...
    @overload
    def msb(
        self, count: None | int = None, rest: None | int = None
    ) -> Signal[BitVector]: ...
    @overload
    def right(self, count: None = None, rest: None = None) -> Signal[Bit]: ...
    @overload
    def right(
        self, count: None | int = None, rest: None | int = None
    ) -> Signal[BitVector]: ...
    @overload
    def left(self, count: None = None, rest: None = None) -> Signal[Bit]: ...
    @overload
    def left(
        self, count: None | int = None, rest: None | int = None
    ) -> Signal[BitVector]: ...

    #
    # casts
    #
    @property
    def unsigned(self: Signal[VEC_T]) -> Signal[Unsigned]: ...
    @unsigned.setter
    def unsigned(
        self: Signal[VEC_T], value: TypeQualifier[Unsigned] | Unsigned | int
    ): ...
    @property
    def signed(self: Signal[VEC_T]) -> Signal[Signed]: ...
    @signed.setter
    def signed(self, value: TypeQualifier[Signed] | Signed | int): ...
    @property
    def bitvector(self: Signal[VEC_T]) -> Signal[BitVector]: ...
    @bitvector.setter
    def bitvector(
        self: Signal[VEC_T], value: TypeQualifier[BitVector] | BitVector | str
    ): ...

    #
    #
    #

    @property
    def next(self) -> typing.NoReturn: ...
    @next.setter
    def next(self, value) -> None: ...
    def __ilshift__(self: Self, value) -> Self: ...
    @property
    def push(self) -> typing.NoReturn: ...
    @push.setter
    def push(self, value) -> None: ...
    def __ixor__(self: Self, value) -> Self: ...
    #
    #
    def _assign_(self, value, assign_mode: AssignMode) -> None: ...

class Port(typing.Generic[T, DIR], Signal[T]):
    #
    #
    #
    @overload
    def __getitem__(self, arg: int) -> Port[Bit, DIR]: ...
    @overload
    def __getitem__(self, arg: slice) -> Port[BitVector, DIR]: ...
    @overload
    def __getitem__(self, arg: tuple | list) -> Temporary[BitVector]: ...
    @overload
    def lsb(self, count: None = None, rest: None = None) -> Port[Bit, DIR]: ...
    @overload
    def lsb(
        self, count: None | int = None, rest: None | int = None
    ) -> Port[BitVector, DIR]: ...
    @overload
    def msb(self, count: None = None, rest: None = None) -> Port[Bit, DIR]: ...
    @overload
    def msb(
        self, count: None | int = None, rest: None | int = None
    ) -> Port[BitVector, DIR]: ...
    @overload
    def right(self, count: None = None, rest: None = None) -> Port[Bit, DIR]: ...
    @overload
    def right(
        self, count: None | int = None, rest: None | int = None
    ) -> Port[BitVector, DIR]: ...
    @overload
    def left(self, count: None = None, rest: None = None) -> Port[Bit, DIR]: ...
    @overload
    def left(
        self, count: None | int = None, rest: None | int = None
    ) -> Port[BitVector, DIR]: ...

    #
    # casts
    #
    @property
    def unsigned(self: Port[VEC_T, DIR]) -> Port[Unsigned, DIR]: ...
    @unsigned.setter
    def unsigned(
        self: Port[VEC_T, DIR], value: TypeQualifier[Unsigned] | Unsigned | int
    ): ...
    @property
    def signed(self: Port[VEC_T, DIR]) -> Port[Signed, DIR]: ...
    @signed.setter
    def signed(self: Port[VEC_T, DIR], value: TypeQualifier[Signed] | Signed | int): ...
    @property
    def bitvector(self: Port[VEC_T, DIR]) -> Port[BitVector, DIR]: ...
    @bitvector.setter
    def bitvector(
        self: Port[VEC_T, DIR], value: TypeQualifier[BitVector] | BitVector | str
    ): ...
    #
    #
    #

    class Direction(enum.Enum):
        class INPUT: ...
        class OUTPUT: ...
        class INOUT: ...

        def is_input(self) -> bool: ...
        def is_output(self) -> bool: ...
        def is_inout(self) -> bool: ...

    @classmethod
    def is_input(cls) -> bool: ...
    @classmethod
    def is_output(cls) -> bool: ...
    @classmethod
    def is_inout(cls) -> bool: ...
    @staticmethod
    def input(
        Wrapped: type[U], *, name: str | None = None
    ) -> Port[U, Port.Direction.INPUT]: ...
    @staticmethod
    def output(
        Wrapped: type[U], *, default=None, name: str | None = None
    ) -> Port[U, Port.Direction.OUTPUT]: ...
    @staticmethod
    def inout(
        Wrapped: type[U], *, default=None, name: str | None = None
    ) -> Port[U, Port.Direction.INOUT]: ...
    @classmethod
    def direction(cls) -> Port.Direction: ...

class Variable(typing.Generic[T], TypeQualifier[T]):
    #
    #
    #
    @overload
    def __getitem__(self, arg: int) -> Variable[Bit]: ...
    @overload
    def __getitem__(self, arg: slice) -> Variable[BitVector]: ...
    @overload
    def __getitem__(self, arg: tuple | list) -> Temporary[BitVector]: ...
    @overload
    def lsb(self, count: None = None, rest: None = None) -> Variable[Bit]: ...
    @overload
    def lsb(
        self, count: None | int = None, rest: None | int = None
    ) -> Variable[BitVector]: ...
    @overload
    def msb(self, count: None = None, rest: None = None) -> Variable[Bit]: ...
    @overload
    def msb(
        self, count: None | int = None, rest: None | int = None
    ) -> Variable[BitVector]: ...
    @overload
    def right(self, count: None = None, rest: None = None) -> Variable[Bit]: ...
    @overload
    def right(
        self, count: None | int = None, rest: None | int = None
    ) -> Variable[BitVector]: ...
    @overload
    def left(self, count: None = None, rest: None = None) -> Variable[Bit]: ...
    @overload
    def left(
        self, count: None | int = None, rest: None | int = None
    ) -> Variable[BitVector]: ...

    #
    # casts
    #
    @property
    def unsigned(self) -> Variable[Unsigned]: ...
    @unsigned.setter
    def unsigned(self, value: TypeQualifier[Unsigned] | Unsigned | int): ...
    @property
    def signed(self) -> Variable[Signed]: ...
    @signed.setter
    def signed(self, value: TypeQualifier[Signed] | Signed | int): ...
    @property
    def bitvector(self) -> Variable[BitVector]: ...
    @bitvector.setter
    def bitvector(self, value: TypeQualifier[BitVector] | BitVector | str): ...
    #
    #
    #
    @property
    def value(self): ...
    @value.setter
    def value(self, value) -> typing.NoReturn: ...
    def __imatmul__(self: Self, value) -> Self: ...

    #
    #
    def _assign_(self, value, assign_mode: AssignMode) -> None: ...

class Temporary(typing.Generic[T], TypeQualifier[T]):
    #
    #
    #
    @overload
    def __getitem__(self, arg: int) -> Temporary[Bit]: ...
    @overload
    def __getitem__(self, arg: slice) -> Temporary[BitVector]: ...
    @overload
    def __getitem__(self, arg: tuple | list) -> Temporary[BitVector]: ...
    @overload
    def lsb(self, count: None = None, rest: None = None) -> Temporary[Bit]: ...
    @overload
    def lsb(
        self, count: None | int = None, rest: None | int = None
    ) -> Temporary[BitVector]: ...
    @overload
    def msb(self, count: None = None, rest: None = None) -> Temporary[Bit]: ...
    @overload
    def msb(
        self, count: None | int = None, rest: None | int = None
    ) -> Temporary[BitVector]: ...
    @overload
    def right(self, count: None = None, rest: None = None) -> Temporary[Bit]: ...
    @overload
    def right(
        self, count: None | int = None, rest: None | int = None
    ) -> Temporary[BitVector]: ...
    @overload
    def left(self, count: None = None, rest: None = None) -> Temporary[Bit]: ...
    @overload
    def left(
        self, count: None | int = None, rest: None | int = None
    ) -> Temporary[BitVector]: ...

    #
    # casts
    #
    @property
    def unsigned(self) -> Temporary[Unsigned]: ...
    @unsigned.setter
    def unsigned(self, value: TypeQualifier[Unsigned] | Unsigned | int): ...
    @property
    def signed(self) -> Temporary[Signed]: ...
    @signed.setter
    def signed(self, value: TypeQualifier[Signed] | Signed | int): ...
    @property
    def bitvector(self) -> Temporary[BitVector]: ...
    @bitvector.setter
    def bitvector(self, value: TypeQualifier[BitVector] | BitVector | str): ...

class Generic: ...
