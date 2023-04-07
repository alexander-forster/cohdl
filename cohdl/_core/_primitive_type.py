from __future__ import annotations


class _PrimitiveType:
    """
    all types, that can be wrapped in a type qualifier
    derive from this type
    """

    pass


def is_primitive_type(t):
    return issubclass(t, _PrimitiveType)


def is_primitive(obj):
    return isinstance(obj, _PrimitiveType)
