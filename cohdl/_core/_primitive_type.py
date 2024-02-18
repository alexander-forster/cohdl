from __future__ import annotations

from ._intrinsic import _intrinsic


class _PrimitiveType:
    """
    all types, that can be wrapped in a type qualifier
    derive from this type
    """

    @_intrinsic
    def __ilshift__(self, other):
        raise AssertionError(
            f"primitive type '{type(self)}' must be type qualified to support assignment"
        )

    @_intrinsic
    def __imatmul__(self, other):
        raise AssertionError(
            f"primitive type '{type(self)}' must be type qualified to support assignment"
        )

    @_intrinsic
    def __ixor__(self, other):
        raise AssertionError(
            f"primitive type '{type(self)}' must be type qualified to support assignment"
        )

    @property
    def next(self):
        raise AssertionError(
            "attempt to use 'next' property on a primitive type, a type qualifier is required"
        )

    @property
    def value(self):
        raise AssertionError(
            "attempt to use 'value' property on a primitive type, a type qualifier is required"
        )

    @property
    def push(self):
        raise AssertionError(
            "attempt to use 'push' property on a primitive type, a type qualifier is required"
        )

    @next.setter
    def next(self, value):
        raise AssertionError(
            "attempt to use 'next' property on a primitive type, a type qualifier is required"
        )

    @next.setter
    def value(self, value):
        raise AssertionError(
            "attempt to use 'value' property on a primitive type, a type qualifier is required"
        )

    @next.setter
    def push(self, value):
        raise AssertionError(
            "attempt to use 'push' property on a primitive type, a type qualifier is required"
        )


def is_primitive_type(t):
    if not isinstance(t, type):
        return False
    else:
        return issubclass(t, _PrimitiveType)


def is_primitive(obj):
    return isinstance(obj, _PrimitiveType)
