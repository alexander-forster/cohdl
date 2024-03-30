from __future__ import annotations

from typing import Callable

from ._type_qualifier import Port, Generic
from ._collect_ast_and_scope import FunctionDefinition, InstantiatedFunction
from cohdl.utility.source_location import SourceLocation
import enum
import inspect

#
#
#

_block_stack: list[Block] = []


class Block:
    @staticmethod
    def enter_block(block: Block):
        if len(_block_stack) != 0:
            _block_stack[-1].add_subblock(block)

        _block_stack.append(block)

    @staticmethod
    def exit_block():
        block = Block.current_block()

        for handler in block._exit_handlers[::-1]:
            handler()

        return _block_stack.pop()

    @staticmethod
    def current_block():
        return _block_stack[-1]

    @staticmethod
    def register_context(ctx: Context):
        assert (
            len(_block_stack) != 0
        ), "cannot register context because no parent block exists"

        _block_stack[-1].add_context(ctx)

    @staticmethod
    def on_exit(callable):
        assert (
            len(_block_stack) != 0
        ), "Block.on_exit can only be used inside a block definition"

        _block_stack[-1]._add_exit_handler(callable)

    def __init__(self, name, attributes: dict):
        self._name = name

        self._attributes = attributes
        self._subcontext: list[Context] = []
        self._subblocks: list[Block] = []
        self._exit_handlers: list = []

    def __enter__(self):
        Block.enter_block(self)

    def __exit__(self, exc_type, exc_value, traceback):
        Block.exit_block()

    def _add_exit_handler(self, handler):
        self._exit_handlers.append(handler)

    def add_context(self, ctx: Context):
        self._subcontext.append(ctx)

    def add_subblock(self, block: Block):
        self._subblocks.append(block)

    def contained_contexts(self):
        return self._subcontext

    def contained_blocks(self):
        return self._subblocks


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
        if len(generics) != 0:
            assert extern, "generics only supported to instantiate external entities"

        if extern:
            assert architecture in (
                None,
                Entity.architecture,
            ), "extern entities cannot define an architecture"
        else:
            assert (
                architecture is not None
            ), "non extern entities must specify an architecture"

        self.name = name
        self.architecture = architecture
        self.extern = extern
        self.ports = ports
        self.generics = generics
        self.instantiated = None
        self.instantiated_template = None

        self.attributes = attributes if attributes is not None else {}

    def add_port(self, name, port):
        #
        # this method is required for board definition classes
        # where ports are reserved while architecture is executed
        #
        self.ports[name] = port


class Entity(Block):
    _info: EntityInfo

    def __init_subclass__(
        cls,
        name: str | None = None,
        extern: bool = False,
        attributes: dict | None = None,
        **kwargs,
    ):
        architecture = cls.architecture

        name = cls.__name__ if name is None else name

        if hasattr(cls, "_info"):
            ports = dict(cls._info.ports)
            generics = dict(cls._info.generics)

            if attributes is None:
                attributes = dict(cls._info.attributes)
            else:
                attributes = {**cls._info.attributes, **attributes}
        else:
            ports = {}
            generics = {}

        for key, value in cls.__dict__.items():
            if isinstance(value, Port):
                ports[key] = value
                value._name = key
            elif isinstance(value, Generic):
                generics[key] = value
                value._name = key

        cls._info = EntityInfo(
            name,
            ports,
            generics,
            architecture=architecture,
            extern=extern,
            attributes=attributes,
        )

    def __init__(self, **kwargs):
        if hasattr(self, "_cohdl_init_started"):
            return
        self._cohdl_init_started = True

        info = self._info
        super().__init__(info.name, info.attributes)

        self.port_definitions = {}
        self.generic_definitions = {}

        for name, value in kwargs.items():
            if name in info.ports:
                self.port_definitions[name] = value
            elif name in info.generics:
                self.generic_definitions[name] = value
            else:
                raise AssertionError(f"invalid argument '{name}'")

        for name, port in info.ports.items():
            if not port.is_output():
                assert (
                    name in self.port_definitions
                ), f"no definition provided for input port '{name}'"
            else:
                if name in self.port_definitions:
                    port_def = self.port_definitions[name]
                    port_decl = info.ports[name]

                    if port_def is not port_decl:
                        # remove default values from signals, that are
                        # driven from instantiated entities
                        # (prevents some errors due to multiple drivers)
                        self.port_definitions[name]._default = None

        for name, generic in info.generics.items():
            if not generic.has_default():
                assert (
                    name in self.generic_definitions
                ), f"no definition provided for generic '{name}'"

        with self:
            if not info.extern and info.instantiated is None:
                # call architecture to collect contained
                # subinstances and synthesizable contexts
                assert (
                    info.architecture is not None
                ), f"entity type {type(self)} has no architecture method"

                # enter block is required, to collect contained
                # subblocks or contexts
                # after exit block, subblocks and contexts will
                # be added to the parent block of self
                info.architecture(self)
                info.instantiated = self

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

        Block.register_context(self)

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
):
    if captured_functions is not None:
        for captured in captured_functions:
            if inspect.iscoroutine(captured):
                FunctionDefinition.from_coroutine(captured)
            else:
                FunctionDefinition.from_callable(captured)

    attributes = {} if attributes is None else attributes
    return Context(fn, ContextType.SEQUENTIAL, name, attributes, source_location)


def concurrent_context(
    fn,
    *,
    name=None,
    attributes: dict | None = None,
    source_location: SourceLocation | None = None,
    captured_functions: list | None = None,
):
    if captured_functions is not None:
        for captured in captured_functions:
            FunctionDefinition.from_callable(captured)

    attributes = {} if attributes is None else attributes
    return Context(fn, ContextType.CONCURRENT, name, attributes, source_location)
