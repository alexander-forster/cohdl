from __future__ import annotations

from typing import Callable

from ._type_qualifier import Port
from ._collect_ast_and_scope import FunctionDefinition, InstantiatedFunction
from cohdl.utility.source_location import SourceLocation
import enum

#
#
#

def on_block_exit(callable):
    """
    Register a callable that takes no arguments to be run once the compiler exits the current Block.
    """

class Block:
    def __init__(self, name, attributes: dict): ...
    def __enter__(self) -> None: ...
    def __exit__(self, exc_type, exc_value, traceback): ...

class EntityInfo:
    def __init__(
        self,
        name: str,
        ports: dict,
        generics: dict,
        *,
        architecture: Callable | None = None,
        extern: bool = False,
        attributes: dict | None = None,
    ):
        self.name = name
        self.architecture = architecture
        self.extern = extern
        self.ports = ports
        self.generics = generics
        self.instantiated = None
        self.instantiated_template = None
        self.attributes = attributes if attributes is not None else {}

    def add_port(self, name: str, port: Port):
        """
        Add a new port to an existing entity class.
        Usually the function is used in the `architecture` method
        of the corresponding entity.

        This function should not be called directly. Use `std.add_entity_port` instead.
        """

class Entity(Block):
    _cohdl_info: EntityInfo

    def __init_subclass__(
        cls,
        name: str | None = None,
        extern: bool = False,
        attributes: dict | None = None,
        **kwargs,
    ): ...
    def __init__(
        self,
        **kwargs,
    ): ...
    def architecture(self): ...

#
#
#

class ContextType(enum.Enum):
    SEQUENTIAL = enum.auto()
    CONCURRENT = enum.auto()

class Context:
    def __init__(
        self,
        fn: Callable,
        context_type: ContextType,
        name: str | None,
        attributes: dict,
        source_loc: SourceLocation | None = None,
    ):
        self._fn = fn
        self._name = fn.__name__ if name is None else name
        self._fn_def = FunctionDefinition.from_callable(fn)
        self._context_type = context_type
        self._attributes = attributes

        self._source_loc = (
            SourceLocation.from_function(fn) if source_loc is None else source_loc
        )

    def attributes(self):
        return self._attributes

    def name(self):
        return self._name

    def source_location(self):
        return self._source_loc

    def instantiate_fn(self) -> InstantiatedFunction:
        return self._fn_def.bind_args([], {})

    def context_type(self):
        return self._context_type

def sequential_context(
    fn,
    *,
    name=None,
    attributes: dict | None = None,
    source_location: SourceLocation | None = None,
    captured_functions: list | None = None,
) -> Context: ...
def concurrent_context(
    fn,
    *,
    name=None,
    attributes: dict | None = None,
    source_location: SourceLocation | None = None,
    captured_functions: list | None = None,
) -> Context: ...
