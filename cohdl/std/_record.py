from __future__ import annotations

import inspect

from cohdl._core import AssignMode, Null, Full
from cohdl._core._intrinsic import _intrinsic
from cohdl.utility import TextBlock

from ._core_utility import (
    count_bits,
    from_bits,
    to_bits,
    concat,
    Value,
    Ref,
)

from ._assignable_type import AssignableType
from ._template import Template, _TemplateMode
from ._prefix import NamedQualifier
from ._exception import StdExceptionHandler, RefQualifierFail


@_intrinsic
def _is_in(value, container):
    return value in container


@_intrinsic
def _args_to_kwargs(kwargs, args, names):
    for arg, name in zip(args, names):
        assert (
            name not in kwargs
        ), f"duplicate definition of '{name}' as positional and keyword argument"
        kwargs[name] = arg


@_intrinsic
def _make_serializable(cls: Record):
    # lookup in dict so values are recalculated for every derived class
    if "_cohdlstd_bitcount" in cls.__dict__:
        return

    slice_map = {}
    elem_start = 0

    for name, elem_type in cls._cohdlstd_record_annotations.items():
        width = count_bits(elem_type)
        slice_map[name] = slice(elem_start + width - 1, elem_start)
        elem_start = elem_start + width

    assert elem_start != 0, "record does not contain any elements to serialize"

    cls._cohdlstd_bitcount = elem_start
    cls._cohdlstd_slice_map = slice_map


@_intrinsic
def _get_reverse_elem_list(self: Record):
    # returns the elements of this record in reverse
    # declaration order so they can be serialized using std.concat

    return [getattr(self, name) for name in self._cohdlstd_record_annotations.keys()][
        ::-1
    ]


class Record(AssignableType, Template):
    # _cohdlstd_bitcount: int
    # _cohdlstd_slice_map: dict[str, slice]

    @classmethod
    def _make_ref_(cls, *args, **kwargs):
        return cls(*args, **kwargs, _qualifier_=Ref)

    @_intrinsic
    def __new__(cls, *args, **kwargs):
        # override __new__ because Template.__new__ does
        # not work for non-template Records
        inst = object.__new__(cls)
        return inst

    def _assign_(self, source, mode: AssignMode) -> None:
        if isinstance(source, dict):
            for name, value in source.items():
                getattr(self, name)._assign_(value, mode)
        elif source is Null or source is Full:
            for name, value in self.__dict__.items():
                value._assign_(source, mode)
        else:
            assert isinstance(source, type(self))
            self._assign_(source.__dict__, mode)

    def __init_subclass__(cls) -> None:
        if cls._template_meta_.mode is _TemplateMode.ROOT:
            # record derived without template arguments
            module_dict = inspect.getmodule(cls).__dict__

            try:
                annotations = {
                    name: eval(value, module_dict)
                    for name, value in cls.__annotations__.items()
                }
            except TypeError as err:
                err.add_note(
                    "add 'from __future__ import annotations' at the top of the file declaring this record"
                )
                raise
        else:
            # record derived with template arguments

            annotations = cls._template_meta_.annotations
            annotations = {} if annotations is None else annotations

        if hasattr(cls, "_cohdlstd_record_annotations"):
            overlap = cls._cohdlstd_record_annotations.keys() & annotations.keys()
            assert (
                len(overlap) == 0
            ), f"record elements '{overlap}' would be overwritten"
            annotations = {**cls._cohdlstd_record_annotations, **annotations}

        cls._cohdlstd_record_annotations = annotations

    def __init__(self, *args, _qualifier_=Value, **kwargs):
        elem_types = self._cohdlstd_record_annotations

        if len(args) == len(kwargs) == 0:
            # default constructor
            for name, elem_type in elem_types.items():
                setattr(self, name, NamedQualifier[_qualifier_, name][elem_type]())

            _init_members = False
        elif len(args) == 1 and len(kwargs) == 0:
            arg = args[0]

            if arg is Null or arg is Full:
                _init_members = False
                for name, elem_type in elem_types.items():
                    setattr(
                        self, name, NamedQualifier[_qualifier_, name][elem_type](arg)
                    )
            elif type(arg) is type(self):
                _init_members = False
                # copy constructor
                self.__init__(**arg.__dict__, _qualifier_=_qualifier_)
            else:
                _init_members = True
        else:
            _init_members = True

        if _init_members:
            _args_to_kwargs(kwargs, args, elem_types)

            if len(kwargs) != len(elem_types):
                missing = elem_types.keys() - kwargs.keys()
                additional = kwargs.keys() - elem_types.keys()

                if len(missing) == 0:
                    raise AssertionError(
                        f"argument error: additional args = {additional}"
                    )

                if len(additional) == 0:
                    raise AssertionError(f"argument error: missing args = {missing}")

                raise AssertionError(
                    f"argument error: missing args = {missing}, additional args = {additional}"
                )

            for name, val in kwargs.items():
                expected_type = elem_types[name]
                setattr(self, name, _qualifier_[expected_type](val))

    @classmethod
    @_intrinsic
    def _count_bits_(cls):
        _make_serializable(cls)
        return cls._cohdlstd_bitcount

    @classmethod
    def _from_bits_(cls, bits, qualifier):
        _make_serializable(cls)
        assert bits.width == cls._count_bits_()

        error_text = [
            "Deserialization using std.Ref qualifier failed because",
            "record type '{}' is not trivially serializable.".format(cls),
            "To fix this error, either use a different qualifier (std.Value) or adjust the type.",
            "Records are trivially serializable is all their member are.",
            "  - allowed     (Bit/BitVector/Signed/Unsigned)",
            "  - not allowed (bool/int/arrays)",
        ]

        with StdExceptionHandler(info=error_text, type=RefQualifierFail):

            result = cls(
                **{
                    name: from_bits[elem_type](
                        bits[cls._cohdlstd_slice_map[name]], qualifier
                    )
                    for name, elem_type in cls._cohdlstd_record_annotations.items()
                },
                # use Ref qualifier because outer qualifier has already been
                # applied during dict construction
                _qualifier_=Ref,
            )

        return result

    def _to_bits_(self):
        _make_serializable(type(self))
        return concat(*[to_bits(elem) for elem in _get_reverse_elem_list(self)])

    @_intrinsic
    def __repr__(self):
        args = ", ".join(f"{name}={value!r}" for name, value in self.__dict__.items())
        return f"{type(self).__name__}({args})"

    @_intrinsic
    def _str_impl(self, elem_name=None):
        type_name = type(self).__name__

        return TextBlock(
            title=type_name if elem_name is None else f"{elem_name}={type_name}",
            content=[
                (
                    f"{name}={value!s}"
                    if not isinstance(value, Record)
                    else value._str_impl(name)
                )
                for name, value in self.__dict__.items()
            ],
            indent=True,
        )

    @_intrinsic
    def __str__(self):
        return self._str_impl().dump()

    def __eq__(self, other):
        return all(
            [value == other.__dict__[name] for name, value in self.__dict__.items()]
        )

    def __ne__(self, other):
        return any(
            [value != other.__dict__[name] for name, value in self.__dict__.items()]
        )
