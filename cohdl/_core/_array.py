from __future__ import annotations


from ._primitive_type import is_primitive_type, _PrimitiveType
from ._intrinsic import _intrinsic


class _MetaArray(type):
    _SubTypes: dict[tuple, type]
    _elem_type: type
    _shape: tuple

    @_intrinsic
    def __getitem__(cls, slice):
        assert isinstance(slice, tuple)
        assert len(slice) == 2
        assert isinstance(slice[0], type)

        elem_type = slice[0]
        shape = tuple(slice[1:])

        assert is_primitive_type(elem_type)

        content_type = (elem_type, shape)

        if content_type in cls._SubTypes:
            return cls._SubTypes[content_type]

        new_type = type(
            cls.__name__, (cls,), {"_elem_type": elem_type, "_shape": shape}
        )
        cls._SubTypes[content_type] = new_type
        return new_type

    @_intrinsic
    def __str__(cls):
        shape = ", ".join(str(dim) for dim in cls._shape)
        return f"{cls.__name__}[{cls._elem_type}, {shape}]"


class Array(_PrimitiveType, metaclass=_MetaArray):
    _SubTypes = {}
    _elem_type: type
    _shape: tuple

    @classmethod
    @property
    def shape(cls):
        return cls._shape

    @classmethod
    @property
    def elemtype(cls):
        return cls._elem_type

    @_intrinsic
    def __init__(self, val=None):
        shape = self._shape

        if isinstance(val, Array):
            val = val._value

        if isinstance(val, (list, tuple)):
            assert len(shape) == 1 and len(val) <= shape[0]
            self._value = [self._elem_type(v) for v in val]
        else:
            assert val is None, "invalid array type"
            self._value = None

    @_intrinsic
    def __getitem__(self, slice):
        if not isinstance(slice, tuple):
            slice = (slice,)

        assert len(slice) == len(self._shape)
        # TODO: multidimensional array
        assert len(slice) == 1
        return self._elem_type()

    @_intrinsic
    def __setitem__(self, slice, arg):
        raise AssertionError(
            "array set item not supported outside synthesizable contexts"
        )

    @_intrinsic
    def _assign(self, value):
        assert isinstance(value, Array)
        assert value.shape[0] == self.shape[0]

        self_val = self.elemtype()

        for val in value._value:
            self_val._assign(val)

    @_intrinsic
    def copy(self) -> Array:
        return type(self)(self._value)

    @_intrinsic
    def __hash__(self):
        return sum(self._shape)

    @_intrinsic
    def __str__(self) -> str:
        return self.__repr__()

    @_intrinsic
    def __repr__(self) -> str:
        return f"{type(self)}()"
