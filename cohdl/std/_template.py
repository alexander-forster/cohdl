from __future__ import annotations

import inspect
import sys

import enum
from dataclasses import dataclass

from cohdl._core._intrinsic import _intrinsic
from ._core_utility import nop


class _TemplateMode(enum.Enum):
    ROOT = enum.auto()
    DECLARATION = enum.auto()
    SPECIALIZED = enum.auto()


class _TemplateMeta:
    def __init__(
        self,
        mode: _TemplateMode,
        argtype: type | None = None,
        instances: dict | None = None,
        original_class_getitem=None,
        annotations: dict | None = None,
        arg=None,
    ):
        self.arg = arg
        self.mode = mode
        self.argtype = argtype
        self.instances: dict[type, dict[any, type]] = instances
        self.original_class_getitem = original_class_getitem
        self.annotations = annotations

    def instance_exists(self, specialized_type: type, template_arg):
        specialized_cache = self.instances.setdefault(specialized_type, {})
        return template_arg in specialized_cache

    def get_instance(self, specialized_type: type, template_arg):
        return self.instances[specialized_type][template_arg]

    def add_instance(self, specialized_type: type, template_arg, instance):
        specialized_cache = self.instances.setdefault(specialized_type, {})
        assert (
            template_arg not in specialized_cache
        ), "internal error: template arg already in cache"
        specialized_cache[template_arg] = instance


@_intrinsic
def class_getitem_specialize(cls: type[Template], args):
    meta = cls._template_meta_

    template_arg = meta.argtype(args)

    if meta.instance_exists(cls, template_arg):
        return meta.get_instance(cls, template_arg)

    # instantiate and add new type early
    # so nested template types are possible
    #
    # shadow __init_subclass__ with a std.nop
    # because the class is not completely initialized at this
    # point. Explicitly call the original __init_subclass__
    # at the end of this function.
    newtype = type(
        f"{cls.__name__}[{template_arg}]",
        (cls,),
        {"__init_subclass__": nop},
    )

    meta.add_instance(cls, template_arg, newtype)

    class_members = {}

    if hasattr(cls, "__class_getitem__"):
        class_members["__class_getitem__"] = cls.__class_getitem__

    template_annotations = {}

    # adopted from typing.get_type_hints
    for base in reversed(cls.__mro__):
        base_globals = getattr(sys.modules.get(base.__module__, None), "__dict__", {})
        ann = base.__dict__.get("__annotations__", {})

        base_locals = {
            name: val if val is not meta.argtype else template_arg
            for name, val in vars(base).items()
        }

        base_globals = {
            name: val if val is not meta.argtype else template_arg
            for name, val in base_globals.items()
        }

        base_globals, base_locals = base_locals, base_globals

        for name, value in ann.items():
            try:
                template_annotations[name] = eval(value, base_globals, base_locals)
            except TypeError as err:
                err.add_note(
                    f"maybe you are missing 'from __future__ import annotations' in {base.__module__}"
                )
                raise err
            except BaseException as err:
                raise err

    newdict = {
        **class_members,
        **template_annotations,
        "_template_meta_": _TemplateMeta(
            mode=_TemplateMode.SPECIALIZED,
            argtype=meta.argtype,
            instances=None,
            original_class_getitem=None,
            annotations=template_annotations,
            arg=template_arg,
        ),
    }

    for name, value in newdict.items():
        setattr(newtype, name, value)

    newtype._template_specialize_()

    # remove __init_subclass__ defined at the start
    # of this function
    delattr(newtype, "__init_subclass__")
    assert hasattr(newtype, "__init_subclass__")
    newtype.__init_subclass__()

    return newtype


class Template:
    _template_meta_ = _TemplateMeta(_TemplateMode.ROOT)

    @_intrinsic
    def __class_getitem__(cls, args):
        assert (
            cls._template_meta_.mode is _TemplateMode.ROOT
        ), "internal error: expected template mode ROOT"
        argtype = args
        assert isinstance(args, type), "Template expects a type argument"
        assert (
            argtype.__hash__ is not object.__hash__
        ), f"TemplatArg({argtype}) must define a hash function"
        assert (
            argtype.__eq__ is not object.__eq__
        ), f"TemplatArg({argtype}) must define an equality comparison operator"

        return type(
            "_TemplateDeclaration",
            (cls,),
            {
                "__class_getitem__": class_getitem_specialize,
                "_template_meta_": _TemplateMeta(
                    mode=_TemplateMode.DECLARATION,
                    argtype=argtype,
                    instances={},
                    original_class_getitem=None,
                ),
            },
        )

    @_intrinsic
    def __new__(cls, *args, **kwargs):
        meta = cls._template_meta_

        assert (
            meta.mode is not _TemplateMode.ROOT
        ), "unconstrained std.Template may not be instantiated"

        if meta.mode is _TemplateMode.SPECIALIZED:
            return super().__new__(cls)

        result_type = cls._template_deduce_(*args, **kwargs)
        result = object.__new__(result_type)
        return result

    @classmethod
    def _template_specialize_(cls):
        pass


@_intrinsic
def _unpack_init(self, real_init, arg):
    if isinstance(arg, tuple):
        real_init(self, *arg)
    else:
        real_init(self, arg)


#
#
#


class _MetaTemplateArg(type):
    @property
    @_intrinsic
    def Type(self):
        class _Type:
            def __new__(cls, arg):
                assert isinstance(arg, type)
                return arg

            def __hash__(self):
                raise AssertionError(
                    "should never be called since __new__ never prevents this class from being instantiated"
                )

            def __eq__(self, other):
                raise AssertionError(
                    "should never be called since __new__ never prevents this class from being instantiated"
                )

        return _Type


class TemplateArg(metaclass=_MetaTemplateArg):

    @_intrinsic
    def __new__(self, cls):
        dataclassed = dataclass(cls, unsafe_hash=True)

        real_init = dataclassed.__init__

        def __init__(self, arg):
            _unpack_init(self, real_init, arg)

        dataclassed.__init__ = __init__

        return dataclassed
