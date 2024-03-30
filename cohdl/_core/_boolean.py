from __future__ import annotations


from ._intrinsic import _intrinsic
from ._primitive_type import _PrimitiveType


class _BooleanLiteral:
    _init_cnt = 0

    def __init__(self, value: bool):
        assert (
            _BooleanLiteral._init_cnt < 2
        ), "only two boolean literals (true and false) can exist"
        _BooleanLiteral._init_cnt += 1
        self._value = value

    def assign(self, other) -> None:
        raise AssertionError("assignment to literal type _BooleanLiteral impossible")

    @_intrinsic
    def __bool__(self) -> bool:
        return self._value

    def __await__(self):
        def coro():
            while not self._value:
                yield
            return self

        return coro()

    @_intrinsic
    def __call__(self, arg) -> _Boolean:
        if self is true:
            return _Boolean(arg)
        else:
            return _Boolean(not arg)


class MetaBoolean(type):
    def __str__(cls):
        return "Boolean"

    def __repr__(cls):
        return "Boolean"


class _Boolean(_PrimitiveType, metaclass=MetaBoolean):
    def __init__(self, value=False):
        self._value = bool(value)

    @property
    def type(self):
        return _Boolean

    def _assign(self, other) -> None:
        if isinstance(other, str):
            assert other in ("0", "1")
            self._value = other == "1"
        else:
            if isinstance(other, int):
                assert other in (0, 1)

            self._value = bool(other)

    def copy(self) -> _Boolean:
        return _Boolean(self._value)

    @_intrinsic
    def __bool__(self) -> bool:
        return self._value

    def __await__(self):
        def coro():
            while not self._value:
                yield
            return self

        return coro()


true = _BooleanLiteral(True)
false = _BooleanLiteral(False)
# TODO
boolean = _Boolean


# Null and Full are not synthesizable in the same sense as
# Bit or Bool. They only serve as helpers for initialization and assignment
# of other types.
# It is not possible to create Signals of type _NullType.


class _NullFullType:
    _init_cnt = 0

    def __init__(self):
        assert (
            _NullFullType._init_cnt <= 1
        ), "only two instances of _NullFullType (Null and Full) can exist"
        _NullFullType._init_cnt += 1

    @_intrinsic
    def __bool__(self):
        return self is Full

    @_intrinsic
    def __inv__(self):
        return Full if self is Null else Null

    @_intrinsic
    def __invert__(self):
        return Full if self is Null else Null


Null = _NullFullType()
"""
magic value that can be assigned to Bit/BitVector types
to set all bits to `0`
"""

Full = _NullFullType()
"""
magic value that can be assigned to Bit/BitVector types
to set all bits to `1`
"""
