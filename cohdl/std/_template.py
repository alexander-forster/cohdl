from __future__ import annotations

import inspect

import enum

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
        self.instances = instances
        self.original_class_getitem = original_class_getitem
        self.annotations = annotations

    def instance_exists(self, template_arg):
        return template_arg in self.instances

    def get_instance(self, template_arg):
        return self.instances[template_arg]

    def add_instance(self, template_arg, instance):
        assert template_arg not in self.instances
        self.instances[template_arg] = instance


@_intrinsic
def class_getitem_specialize(cls: type[Template], args):
    meta = cls._template_meta_

    template_arg = meta.argtype(args)

    if meta.instance_exists(template_arg):
        return meta.get_instance(template_arg)

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

    meta.add_instance(template_arg, newtype)

    class_members = {}

    if hasattr(cls, "__class_getitem__"):
        class_members["__class_getitem__"] = cls.__class_getitem__

    module_dict = inspect.getmodule(cls).__dict__

    template_scope = {
        name: value if value is not meta.argtype else template_arg
        for name, value in module_dict.items()
    }

    template_annotations = {}

    for parent_type in cls.mro():
        if parent_type is Template:
            break

        for name, value in parent_type.__annotations__.items():
            assert not name in template_annotations
            template_annotations[name] = eval(value, template_scope)

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
        assert cls._template_meta_.mode is _TemplateMode.ROOT
        argtype = args
        assert isinstance(args, type)
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
