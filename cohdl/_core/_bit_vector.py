from __future__ import annotations

import enum


import typing
from typing import cast

from cohdl.utility import Span

from cohdl._core._bit import Bit, BitState
from cohdl._core._integer import Integer
from cohdl._core._boolean import _NullFullType, Null
from cohdl._core._intrinsic import _intrinsic
from cohdl._core._primitive_type import _PrimitiveType

Self = typing.TypeVar("Self")


class BitOrder(enum.Enum):
    DOWNTO = enum.auto()
    UPTO = enum.auto()


class _BitVector(type):
    _width: int
    _order: BitOrder
    _SubTypes: dict[tuple, type]

    @_intrinsic
    def __getitem__(cls, size: int | slice):
        if isinstance(size, slice):
            assert size.step is None, "step parameter not allowed in slice argument"
            assert isinstance(size.start, int), "start parameter must be integer"
            assert isinstance(size.stop, int), "stop parameter must be integer"

            if size.start == 0:
                assert size.stop >= 0, "stop value cannot be negative"
                order = BitOrder.UPTO
                width = size.stop + 1
            elif size.stop == 0:
                assert size.start >= 0, "start value cannot be negative"
                order = BitOrder.DOWNTO
                width = size.start + 1
            else:
                raise AssertionError(
                    "invalid BitVector declaration, start or stop must be 0"
                )
        else:
            assert isinstance(size, int)
            assert size >= 0, "vector width must be positive"

            order = BitOrder.DOWNTO
            width = size

        shape = (order, width)

        if shape in cls._SubTypes:
            return cls._SubTypes[shape]

        if cls._SubTypes is BitVector._SubTypes:
            new_type = type(cls.__name__, (cls,), {"_width": width, "_order": order})
        else:
            new_type = type(
                cls.__name__,
                (cls, BitVector[width]),
                {"_width": width, "_order": order},
            )

        cls._SubTypes[shape] = new_type
        return new_type

    @_intrinsic
    def __str__(cls):
        if not hasattr(cls, "_width"):
            return f"{cls.__name__}"

        order = getattr(cls, "_order")
        width = getattr(cls, "_width")

        if order is BitOrder.DOWNTO:
            if width == 0:
                start = 0
                stop = ""
            else:
                start = width - 1
                stop = 0
        else:
            if width == 0:
                start = ""
                stop = 0
            else:
                start = 0
                stop = width - 1

        return f"{cls.__name__}[{start}:{stop}]"

    @classmethod
    def __repr__(cls):
        return cls.__str__(cls)

    @property
    def width(cls):
        return cls._width

    @property
    def order(cls):
        return cls._order


class BitVector(_PrimitiveType, metaclass=_BitVector):
    _SubTypes = {}
    _width: int
    _order: BitOrder

    @property
    def width(self):
        return self._width

    @property
    def order(self):
        return self._order

    @_intrinsic
    def __init__(
        self,
        val: None | BitVector | str | _NullFullType | Span[Bit] = None,
    ):
        if isinstance(val, Span):
            # init bitvector as a span over a subrange of an existing bitvector
            assert self._width == len(val)
            self._value = val
        else:
            # init bitvector as a new parent object

            self._value: Span[Bit] = Span([Bit() for _ in range(self._width)])

            if val is None:
                # no init of _value required
                return

            if isinstance(val, BitVector):
                assert (
                    val._width == self._width
                ), f"width mismatch in vector constructor source-width({val._width}) != target-width({self._width})"
                start_val = val._value
            elif isinstance(val, str):
                assert len(val) == self._width
                start_val = Span.from_iter(val[::-1], Bit)
            elif isinstance(val, _NullFullType):
                start_val = [Bit(val) for _ in range(self._width)]
            else:
                raise AssertionError(
                    f"invalid default value '{val}' for type {type(self)}"
                )

            self._value.apply_zip(
                lambda bit, state: bit._assign(state),
                cast(Span[Bit], start_val),
            )

    @_intrinsic
    def _is_uninitialized(self):
        return all(bit._is_uninitialized() for bit in self._value)

    @_intrinsic
    def __iter__(self):
        return iter(self._value)

    @_intrinsic
    def _bit_str(self) -> str:
        return "".join([str(bit) for bit in self._value][::-1])

    @_intrinsic
    def copy(self):
        return type(self)(Span.from_iter(self._value, lambda bit: bit.copy()))

    @_intrinsic
    def right(self, width=None, rest=None) -> BitVector | Bit:
        if width is None and rest is None:
            return self._value[0]

        if (width is not None) and (rest is not None):
            assert (
                width + rest == self._width
            ), f"width + rest does not equal the vectors width ({width}+{rest} != {self._width})"

        if rest is not None:
            width = self._width - rest
        elif width is None:
            width = 1

        width = int(width)

        assert (
            1 <= width <= self._width
        ), f"invalid subvector width {width} for vector of width {self._width}"

        return BitVector[width](self._value[0:width])

    @_intrinsic
    def left(self, width=None, rest=None) -> BitVector | Bit:
        if width is None and rest is None:
            return self._value[-1]

        if (width is not None) and (rest is not None):
            assert (
                width + rest == self._width
            ), f"width + rest does not equal the vectors width ({width}+{rest} != {self._width})"

        if rest is not None:
            width = self._width - rest
        elif width is None:
            width = 1

        width = int(width)

        assert (
            1 <= width <= self._width
        ), f"invalid subvector width {width} for vector of width {self._width}"

        return BitVector[width](self._value[self._width - width :])

    @_intrinsic
    def lsl(self, cnt=None, fill=None):
        if fill is not None:
            assert cnt is None or cnt is len(fill)
            fill_val = fill
        else:
            if cnt is None:
                fill_val = Bit(0)
            else:
                fill_val = BitVector[cnt](Null)

        return self.right(rest=len(fill_val)) @ fill_val

    @_intrinsic
    def lsr(self, cnt=None, fill=None):
        if fill is not None:
            assert cnt is None or cnt is len(fill)
            fill_val = fill
        else:
            if cnt is None:
                fill_val = Bit(0)
            else:
                fill_val = BitVector[cnt](Null)

        return fill_val @ self.left(rest=len(fill_val))

    @_intrinsic
    def lsb(self, width: int | None = None, rest=None) -> BitVector | Bit:
        if self._order is BitOrder.DOWNTO:
            return self.right(width, rest)
        return self.left(width, rest)

    @_intrinsic
    def msb(self, width=None, rest=None) -> BitVector | Bit:
        if self._order is BitOrder.DOWNTO:
            return self.left(width, rest)
        return self.right(width, rest)

    @_intrinsic
    def _assign(self, other):
        if isinstance(other, _NullFullType):
            other = type(self)(other)
        if isinstance(other, str):
            other = BitVector[len(other)](other)

        assert isinstance(other, BitVector), f"expected BitVector not '{other}'"

        assert (
            self._width == other._width
        ), f"width mismatch in vector assignment (target_width({self._width}) != source_width({other._width}))"

        self._value.apply_zip(lambda bit, other: bit._assign(other), other._value)

    @_intrinsic
    def __bool__(self) -> bool:
        return any([bit for bit in self._value])

    @_intrinsic
    def __invert__(self):
        return type(self)(Span.from_iter(self._value, lambda bit: ~bit))

    @_intrinsic
    def __inv__(self):
        return self.__invert__()

    @_intrinsic
    def __or__(self, other):
        if not isinstance(other, BitVector):
            return NotImplemented

        Self = type(self)
        Other = type(other)

        assert Self is Other, f"type mismatch in binary or ({Self} != {Other})"

        return Self(
            Span.from_zip_iter(self._value, other._value, modifyer=lambda a, b: a | b)
        )

    @_intrinsic
    def __and__(self, other):
        if not isinstance(other, BitVector):
            return NotImplemented

        Self = type(self)
        Other = type(other)

        assert Self is Other, f"type mismatch in binary and ({Self} != {Other})"

        return Self(
            Span.from_zip_iter(self._value, other._value, modifyer=lambda a, b: a & b)
        )

    @_intrinsic
    def __xor__(self, other):
        if not isinstance(other, BitVector):
            return NotImplemented

        Self = type(self)
        Other = type(other)

        assert Self is Other, f"type mismatch in binary xor ({Self} != {Other})"

        return Self(
            Span.from_zip_iter(self._value, other._value, modifyer=lambda a, b: a ^ b)
        )

    @_intrinsic
    def __eq__(self, other: BitVector) -> bool:

        if isinstance(other, _NullFullType):
            if other:
                return all(bit for bit in self._value)
            else:
                return not any(bit for bit in self._value)

        if isinstance(other, str):
            other = BitVector[len(other)](other)
        else:
            assert isinstance(other, BitVector)

            from ._signed import Signed
            from ._unsigned import Unsigned

            if isinstance(other, (Signed, Unsigned)):
                raise AssertionError(
                    "cannot directly compare bitvector to signed/unsigned, cast required"
                )

        assert self.width == other.width, "cannot compare bitvectors of different width"

        for a, b in zip(self._value, other._value):
            if bool(a) != bool(b):
                return False

        return True

    @_intrinsic
    def __ne__(self, other: BitVector) -> bool:
        return not self.__eq__(other)

    @_intrinsic
    def __matmul__(self, rhs: Bit | BitVector) -> BitVector:
        if isinstance(rhs, Bit):
            result = BitVector[self._width + 1]()

            result._value[0]._assign(rhs)
            result._value[1:].apply_zip(
                lambda bit, other: bit._assign(other), self._value
            )

            return result
        elif isinstance(rhs, BitVector):
            result = BitVector[self.width + rhs.width]()

            result._value[rhs.width :].apply_zip(
                lambda bit, other: bit._assign(other), self._value
            )
            result._value[: rhs.width].apply_zip(
                lambda bit, other: bit._assign(other), rhs._value
            )

            return result
        else:
            return NotImplemented

    @_intrinsic
    def __rmatmul__(self, lhs: Bit) -> BitVector:
        assert isinstance(lhs, Bit)

        result = BitVector[self._width + 1]()
        result._value[self._width]._assign(lhs)
        result._value[0 : self._width].apply_zip(
            lambda bit, val: bit._assign(val), self._value
        )

        return result

    @_intrinsic
    def __len__(self) -> int:
        return len(self._value)

    @_intrinsic
    def subvector(self, offset: int, width: int | None = None):
        if width is None:
            width = self.width() - offset

        assert offset >= 0 and offset + width <= self.width()

        if width == 0:
            return BitVector[0]()

        return BitVector[width](self._value)

    @_intrinsic
    def __getitem__(self, key: int | Integer | slice) -> BitVector | Bit:
        if isinstance(key, (tuple, list)):
            first, *rest = key

            if len(rest) == 0:
                if isinstance(first, slice):
                    return self.__getitem__(first)
                else:
                    return self.__getitem__(slice(first, first))
            else:
                return self.__getitem__(first) @ self.__getitem__(rest)
        elif isinstance(key, (int, Integer)):
            key = Integer.decay(key)
            assert 0 <= key < self.width, "index exceeds vector width"
            return self._value[key]
        elif isinstance(key, slice):
            assert key.step is None, "step parameter cannot be used"
            start = Integer.decay(key.start)
            stop = Integer.decay(key.stop)

            width = max(start, stop) - min(start, stop) + 1

            if stop <= start:
                return BitVector[width](self._value[stop : start + 1])
            else:
                raise RuntimeError("not implemented")
        else:
            raise RuntimeError(f"invalid slice parameter <{key}>")

    @_intrinsic
    def __setitem__(self, key: int | Integer | slice, value: Bit | BitVector):
        if not isinstance(key, slice):
            assert isinstance(value, (Bit, BitState))
            self._value[int(key)].assign(value)
        else:
            assert key.step is None, "step parameter cannot be used"
            start = int(key.start)
            stop = int(key.stop)

            assert isinstance(value, BitVector)

            start, stop = sorted([start, stop])

            width = stop - start + 1
            assert len(value) == width

            self._value[start : stop + 1].apply_zip(
                lambda bit, other: bit.assign(other), value._value
            )

    def __hash__(self) -> int:
        return len(self) + 1000

    def __str__(self) -> str:
        return self._bit_str()

    def __repr__(self) -> str:
        return f"{type(self)}({self._bit_str()})"

    @_intrinsic
    @property
    def unsigned(self: BitVector):
        from . import Unsigned

        if isinstance(self, Unsigned):
            return self

        return Unsigned[self._width](self._value)

    @_intrinsic
    @unsigned.setter
    def unsigned(self: BitVector, value):
        self.unsigned._assign(value)

    @_intrinsic
    @property
    def signed(self):
        from . import Signed

        if isinstance(self, Signed):
            return self

        return Signed[self._width](self._value)

    @_intrinsic
    @signed.setter
    def signed(self: BitVector, value):
        self.signed._assign(value)

    @_intrinsic
    @property
    def bitvector(self) -> BitVector:
        from . import Unsigned, Signed

        if not isinstance(self, (Unsigned, Signed)):
            return self

        return BitVector[self._width](self._value)

    @_intrinsic
    @bitvector.setter
    def bitvector(self: BitVector, value):
        self.bitvector._assign(value)
