from __future__ import annotations

import enum
from enum import auto

from ._primitive_type import _PrimitiveType


class Enum(_PrimitiveType, enum.Enum):
    """
    derived Enum class
    defined here, to allow future API changes and to
    separate Enumerations intended for synthesis from other enums
    """

    @classmethod
    def _missing_(cls, value):
        assert value is None

        for val in cls.__members__.values():
            return val

        raise AssertionError("empty enum")

    def _assign(self, value):
        assert type(self) is type(value)
        return self


class EnumFlag(_PrimitiveType, enum.Flag):
    """
    derived EnumFlag class
    defined here, to allow future API changes and to
    separate Enumerations intended for synthesis from other enums
    """

    pass


class DynamicEnum(_PrimitiveType):
    __members__: list[DynamicEnum]

    def _init_new(self, val: int, name: str):
        self.val = val
        self.name = name

    @classmethod
    def _make_new(cls, val: int, name: str | None):
        if name is None:
            if cls.__name__.endswith("_"):
                name = f"{cls.__name__}{val}"
            else:
                name = f"{cls.__name__}_{val}"
        for existing in cls.__members__:
            assert name != existing.name, f"name {name} already exists"

        new_obj = object.__new__(cls)
        new_obj._init_new(len(cls.__members__), name)
        cls.__members__.append(new_obj)
        return new_obj

    def __new__(cls, val: int | DynamicEnum | None = None, name: str | None = None):
        if val is None:
            return cls._make_new(len(cls.__members__), name)
        elif isinstance(val, int) and val == len(cls.__members__):
            return cls._make_new(len(cls.__members__), name)
        else:
            assert type(val) is cls
            val = val.val

        obj = cls.__members__[val]

        if name is not None:
            for existing in cls.__members__:
                if existing is not obj:
                    assert name != existing.name, f"name {name} already exists"

        obj.name = name
        return obj

    def __repr__(self):
        return f"{type(self).__name__}({self.name}, {self.val})"

    def __hash__(self):
        return self.val

    @classmethod
    def reserve(cls, name: str | None = None):
        assert (
            cls is not DynamicEnum
        ), "reserve can only be called on a subclass of DynamicEnum"

        assert not any(
            member.name == name for member in cls.__members__
        ), f"reserving existiong name '{name}' not allowed"

        return cls(name=name)

    @classmethod
    def get(cls, val: int):
        return cls.__members__[val]

    @classmethod
    def count(cls):
        return len(cls.__members__)

    def __init_subclass__(cls) -> None:
        assert cls.mro() == [
            cls,
            DynamicEnum,
            object,
        ], "only single inheritance supported for DynamicEnum"
        cls.__members__ = []
