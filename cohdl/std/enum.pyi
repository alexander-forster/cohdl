from __future__ import annotations

from typing import Generic, TypeVar, Self, overload

from cohdl._core import BitVector
from ._core_utility import Value
from ._assignable_type import AssignableType

T = TypeVar("T")

class Enum(Generic[T], AssignableType):
    """
    `Enum` used to define custom types with literal values.
    The type of the literal is passed as a template argument.

    >>>
    >>> # declare an enumeration with the underlying type `Unsigned[8]`
    >>> class MyEnum(std.Enum[Unsigned[8]]):
    >>>     # declare an enumerator a
    >>>     # will construct a Unsigned[8] using the argument Null
    >>>     a = std.Enum(Null)
    >>>
    >>>     # declare enumerator with value 3 and info text
    >>>     b = std.Enum(3, "enumerator b")
    >>>
    >>>     # shorthand for `c = std.Enum(10)
    >>>     c = 10
    >>>
    >>>     # shorthand for `d = std.Enum(55, "enumerator d")`
    >>>     d = 55, "enumerator d"
    >>>
    >>> def example_usage(inp: MyEnum):
    >>>     my_signal = Signal[MyEnum]()
    >>>     my_signal <<= inp
    >>>
    >>>     if inp == MyEnum.a:
    >>>         return True
    >>>     else:
    >>>         return False
    >>>
    """

    _underlying_: type[T]
    """
    the underlying type wrapped by the Enum
    """

    _default_: Enum[T]
    """
    value used to default construct instances
    """

    __members__: dict[str, Enum[T]]
    """
    dict of all declared enumerators
    """

    @property
    def raw(self) -> T:
        """
        returns the raw value contained in the Enum
        """

    @raw.setter
    def raw(self, value):
        """
        Direct assignment to the contained value.
        Only allowed using one of the operators '<<=', '^=' or '@='.
        """

    @property
    def name(self) -> str:
        """
        Returns the name of the enumerator.
        Only defined for the enumerator literals defined
        in the enum declaration.

        Other instances of Enum are runtime variable and have no
        definite name.
        """

    @property
    def info(self):
        """
        Returns the name of the enumerator.
        Only defined for the enumerator literals defined
        in the enum declaration.

        Other instances of Enum are runtime variable and have no
        definite info.
        """

    @classmethod
    def _count_bits_(cls) -> int: ...
    @classmethod
    def _from_bits_(cls: Self, bits: BitVector, qualifier=Value) -> Self: ...
    def _to_bits_(self) -> BitVector: ...
    @classmethod
    def _unsafe_init_(cls: Self, raw: T, _qualifier_=Value) -> Self:
        """
        Create a new instance of Enum that wraps the provided raw value.
        This is an unsafe operation because it can introduce enumerator values
        that are not part of the declaration.
        """

    @overload
    def __init__(self, val: T, info: str | None = None):
        """
        This overload can only be used to define a new
        enumerator as part of an enum declaration.
        """

    @overload
    def __init__(self, _qualifier_=Value):
        """
        Default initialize.
        The first enumerator defined in the enum declaration is used.
        """

    @overload
    def __init__(self, val: Enum[T] | None = None, _qualifier_=Value):
        """
        Copy initialize from existing instance of Enum.
        """

    def __bool__(self) -> bool: ...
    def __eq__(self, other) -> bool: ...
    def __ne__(self, other) -> bool: ...

class FlagEnum(Enum):
    """
    `FlagEnum` defines the bitwise and/or/xor operators.
    It is otherwise identical to `Enum`.
    """

    def __and__(self: Self, other: Self) -> Self: ...
    def __or__(self: Self, other: Self) -> Self: ...
    def __xor__(self: Self, other: Self) -> Self: ...
