from __future__ import annotations

from typing import Callable

from ._type_qualifier import Port, Generic
from ._collect_ast_and_scope import FunctionDefinition, InstantiatedFunction
from cohdl.utility.source_location import SourceLocation
from ._intrinsic import _intrinsic, _intrinsic_replacement, _IntrinsicInlineEntity
import enum
import inspect

#
#
#

_block_stack: list[Block] = []
_entity_instantiation_handler = None


def _set_entity_instantiation_handler(fn):
    global _entity_instantiation_handler
    _entity_instantiation_handler = fn


def _enter_block(block: Block):
    if len(_block_stack) != 0:
        _block_stack[-1]._cohdl_block_info._subblocks.append(block)

    _block_stack.append(block)


def _exit_block():
    block = _block_stack[-1]

    for handler in block._cohdl_block_info._exit_handlers[::-1]:
        handler()

    return _block_stack.pop()


def _register_block(block: Block):
    if len(_block_stack) != 0:
        _block_stack[-1]._cohdl_block_info._subblocks.append(block)


def _register_context(ctx: Context):
    assert (
        len(_block_stack) != 0
    ), "cannot register context because no parent block exists"

    _block_stack[-1]._cohdl_block_info._subcontext.append(ctx)


def on_block_exit(callable):
    assert (
        len(_block_stack) != 0
    ), "cohdl.on_block_exit can only be used inside a block definition"

    _block_stack[-1]._cohdl_block_info._exit_handlers.append(callable)


class _BlockInfo:
    def __init__(self, name, attributes: dict):
        self._name = name

        self._attributes = attributes
        self._subcontext: list[Context] = []
        self._subblocks: list[Block] = []
        self._exit_handlers: list = []


class Block:

    def __init__(self, name, attributes: dict):
        self._cohdl_block_info = _BlockInfo(name, attributes)


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

        # This should be set to a list of all port names that
        # were available before the entity was instantiated.
        # After the compilation is done, all other ports
        # will be removed from the entity to restore the previous state.
        self.non_dynamic_ports: list[str] = None
        self._entity_type: type = None

        self.attributes = attributes if attributes is not None else {}

    def copy(self):
        # copy needed because _discard_instantiation is called before
        # entity info is passed to later compiler stages
        return EntityInfo(
            name=self.name,
            ports={**self.ports},
            generics={**self.generics},
            architecture=self.architecture,
            extern=self.extern,
            attributes={**self.attributes},
        )

    def _discard_instantiation(self):
        self.instantiated = None
        self.instantiated_template = None

    def _discard_dynamic_ports(self):
        if self.non_dynamic_ports is not None:
            entity_type = self._entity_type

            for port_name in list(self.ports):
                if port_name in self.non_dynamic_ports:
                    continue

                del self.ports[port_name]
                delattr(entity_type, port_name)

        self.non_dynamic_ports = None

    def add_port(self, name, port):
        #
        # this method is required for board definition classes
        # where ports are reserved while architecture is executed
        #
        self.ports[name] = port


class Entity(Block):
    _cohdl_info: EntityInfo

    def __init_subclass__(
        cls,
        name: str | None = None,
        extern: bool = False,
        attributes: dict | None = None,
        **kwargs,
    ):
        architecture = cls.architecture

        name = cls.__name__ if name is None else name

        if hasattr(cls, "_cohdl_info"):
            ports = dict(cls._cohdl_info.ports)
            generics = dict(cls._cohdl_info.generics)

            if attributes is None:
                attributes = dict(cls._cohdl_info.attributes)
            else:
                attributes = {**cls._cohdl_info.attributes, **attributes}
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

        cls._cohdl_info = EntityInfo(
            name,
            ports,
            generics,
            architecture=architecture,
            extern=extern,
            attributes=attributes,
        )

        cls._cohdl_info._entity_type = cls

    @_intrinsic
    def __init__(
        self,
        *,
        _cohdl_internal_ctor=False,
        _cohdl_instantiate_only=False,
        **kwargs,
    ):
        # TODO: check if this check is needed
        if hasattr(self, "_cohdl_init_started"):
            return
        self._cohdl_init_started = True

        info = self._cohdl_info
        super().__init__(info.name, info.attributes)

        if _cohdl_internal_ctor:
            return

        if not info.extern and info.instantiated is None:
            # call architecture to collect contained
            # subinstances and synthesizable contexts
            assert (
                info.architecture is not None
            ), f"entity type {type(self)} has no architecture method"

            # remove possible dynamically added ports
            # (might have been added by previous builds)
            # remove them before the build instead of after because
            # the port info might be inspected after the build.
            # For example when constructing simulation objects.
            info._discard_dynamic_ports()

            global _block_stack

            prev_block_stack = _block_stack

            try:
                # use a clear block stack and an empty instance of the entity
                # class to create the single instantiated entity

                template_instance = type(self)(_cohdl_internal_ctor=True)
                _block_stack = [template_instance]

                info.non_dynamic_ports = set(info.ports)
                info.instantiated = template_instance
                info.architecture(template_instance)

                for handler in template_instance._cohdl_block_info._exit_handlers[::-1]:
                    handler()

                if _entity_instantiation_handler is not None:
                    _entity_instantiation_handler(info)
            finally:
                assert len(_block_stack) == 1
                _block_stack = prev_block_stack

        if _cohdl_instantiate_only:
            return

        self._cohdl_port_definitions = {}
        self._cohdl_generic_definitions = {}

        for name, value in kwargs.items():
            if name in info.ports:
                self._cohdl_port_definitions[name] = value
            elif name in info.generics:
                self._cohdl_generic_definitions[name] = value
            else:
                raise AssertionError(f"invalid argument '{name}'")

        for name, port in info.ports.items():
            if not port.is_output():
                assert (
                    name in self._cohdl_port_definitions
                ), f"no definition provided for input port '{name}'"
            else:
                assert (
                    name in self._cohdl_port_definitions
                ), f"no definition provided for port '{name}'"

                port_def = self._cohdl_port_definitions[name]
                port_decl = info.ports[name]

                if port_def is not port_decl:
                    # remove default values from signals, that are
                    # driven from instantiated entities
                    # (prevents some errors due to multiple drivers)
                    port_def._default = None

        for name, generic in info.generics.items():
            if not generic.has_default():
                assert (
                    name in self._cohdl_generic_definitions
                ), f"no definition provided for generic '{name}'"

        _register_block(self)

        # set port definitions after instantiation so
        # ports are visible while instantiating and
        # connected signals afterwards
        for name in info.ports:
            if name in self._cohdl_port_definitions:
                setattr(self, name, self._cohdl_port_definitions[name])

    @_intrinsic_replacement(__init__)
    def _init_replacement(self, **kwargs):
        self.__init__(**kwargs)
        return _IntrinsicInlineEntity(self)

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

        _register_context(self)

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
