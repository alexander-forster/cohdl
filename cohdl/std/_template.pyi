from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Generic, TypeVar, Self, Any

T = TypeVar("T")
TempArg = TypeVar("TempArg")

class _TemplateMode(enum.Enum):
    ROOT = enum.auto()
    DECLARATION = enum.auto()
    SPECIALIZED = enum.auto()

class _TemplateMeta:
    arg: Any | None
    mode: _TemplateMode
    argtype: type
    instances: dict[str, type[Template]]
    annotations: dict[str, Any]

class Template(Generic[TempArg]):
    """
    Helper class, that implements a basic template functionality
    similar to C++.

    Useful because many `std` functions/containers operate on type
    arguments.

    >>> # Example:
    >>> # a simple template class, that holds two values
    >>> # and checks, their types against the provided template arguments
    >>> class _PairArgs:
    >>>     def __init__(self, args: tuple[type, type]):
    >>>         self._type_first, self._type_second = args
    >>>
    >>>     def __eq__(self, other: _PairArgs):
    >>>         # TemplateArg must define __eq__ to allow templates
    >>>         # instantiated with equivalent arguments to map to the same
    >>>         # specialized template class
    >>>         return (
    >>>             self._type_first == other._type_first
    >>>             and self._type_second == other._type_second
    >>>         )
    >>>
    >>> class Pair(std.Template[_PairArgs]):
    >>>     def __init__(self, first, second):
    >>>         assert type(first) is self._template_arg_._type_first
    >>>         assert type(second) is self._template_arg_._type_second
    >>>         self.first = first
    >>>         self.second = second
    >>>
    >>> a = Pair[int, float](1, 1.23)
    >>> b = Pair[int, str](2, "hello")
    >>> c = Pair[int, float](3, 34.5)
    >>> # templates instantiated with the same arguments
    >>> # map to the same type
    >>> assert type(a) is not type(b)
    >>> assert type(a) is type(c)
    """

    _template_meta_: _TemplateMeta
    """
    this class member contains the result of instantiating `TemplateArg`
    with the arguments used to specialize the template
    """

    @classmethod
    def _template_deduce_(cls, *args, **kwargs) -> type[Template[TemplateArg]]:
        """
        Given a set of constructor arguments, this classmethod
        should return the type fitting the arguments.
        """

    @classmethod
    def _template_specialize_(cls):
        """
        Called at the and of each new template specialization.
        Use to customize the generated types similar to __init_subclass__
        """

    def __class_getitem__(cls: Self, args) -> Self: ...

class TemplateArg:
    Type = T

    def __new__(cls, arg: type[T]) -> type[T]:
        """
        Decorator that adds __init__, __hash__ and __eq__
        Use new instead of __call__ because TemplateArg is a class.

        to a class so it can be used as an argument for std.Template.
        """
