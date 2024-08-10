from __future__ import annotations


from ._primitive_type import is_primitive_type, _PrimitiveType
from ._intrinsic import _intrinsic
from ._enum import Enum
from ._boolean import Null, Full


class _MetaArray(type):
    _SubTypes: dict[tuple, type]

    _elemtype_: type
    _count_: int

    @_intrinsic
    def __len__(cls):
        return cls._count_

    @_intrinsic
    def __getitem__(cls, slice):
        assert (
            isinstance(slice, tuple) and len(slice) == 2
        ), "cohdl.Array[] requires two arguments [DATA_TYPE, SIZE]"

        elemtype, count = slice

        assert isinstance(elemtype, type)
        assert isinstance(count, int)

        assert is_primitive_type(elemtype)

        content_type = (elemtype, count)

        if content_type in cls._SubTypes:
            return cls._SubTypes[content_type]

        new_type = type(
            cls.__name__, (cls,), {"_elemtype_": elemtype, "_count_": count}
        )
        cls._SubTypes[content_type] = new_type
        return new_type

    @_intrinsic
    def __str__(cls):
        return f"{cls.__name__}[{cls._elemtype_}, {cls._count_}]"


class Array(_PrimitiveType, metaclass=_MetaArray):
    _SubTypes = {}
    _elemtype_: type
    _count_: int

    @_intrinsic
    def __init__(self, val=None):
        elemtype = self._elemtype_

        if isinstance(val, Array):
            val = val._value

        if isinstance(val, (list, tuple)):
            assert (
                len(val) <= self._count_
            ), "more default arguments than array elements"
            self._value = [elemtype(v) for v in val]
        elif val is Null or val is Full:
            self._value = [elemtype(val) for _ in range(self._count_)]
        else:
            assert val is None, "invalid array type"
            self._value = None

    @_intrinsic
    def __len__(self):
        return self._count_

    @_intrinsic
    def __getitem__(self, index: int):
        if index < 0:
            raise IndexError(f"negative Array index ({index}) not allowed")

        if index >= self._count_:
            raise IndexError(
                f"index '{index}' not in allowed range [0-{self._count_-1}]"
            )

        if self._value is not None and index < len(self._value):
            return self._value[index]

        elem_type = self._elemtype_

        if issubclass(elem_type, Enum):
            first, *rest = elem_type._member_map_.values()
            return elem_type(first)

        return elem_type()

    @_intrinsic
    def __setitem__(self, slice, arg):
        raise AssertionError(
            "array set item not supported outside synthesizable contexts"
        )

    @_intrinsic
    def _assign(self, value):
        self_val = self._elemtype_()

        if isinstance(value, Array):
            assert (
                value._count_ == self._count_
            ), f"width of source array does not match width of target ({value._count_} != {self._count_})"

            # Dummy assignment, does not actually assign to array members
            # to avoid creating potentially large number of elements.
            # Only used to ensure, that the assignment is sound.
            self_val._assign(value._elemtype_())

        elif isinstance(value, (list, tuple)):
            assert (
                len(value) == self._count_
            ), f"width of source does not match width of target ({len(value)} != {len(self._count_)})"

            for val in value:
                # Dummy assignment, does not actually assign to array members
                # to avoid creating potentially large number of elements.
                # Only used to ensure, that the assignment is sound.
                self_val._assign(val)
        else:
            assert value is Null or value is Full, f"cannot assigned {value} to array"

    @_intrinsic
    def copy(self) -> Array:
        return type(self)(self._value)

    @_intrinsic
    def __hash__(self):
        return hash(self._elemtype_, self._count_)

    @_intrinsic
    def __str__(self) -> str:
        return self.__repr__()

    @_intrinsic
    def __repr__(self) -> str:
        return f"{type(self)}()"
