from __future__ import annotations

import inspect
import typing

from cohdl._core._type_qualifier import TypeQualifier, Temporary
from cohdl._core import Bit, BitVector, select_with
from cohdl._core._intrinsic import _intrinsic


@_intrinsic
def iscouroutinefunction(fn):
    return inspect.iscoroutinefunction(fn)


def instance_check(val, type):
    return isinstance(TypeQualifier.decay(val), type)


def subclass_check(val, type):
    return issubclass(TypeQualifier.decay(val), type)


#
#
#


class _UncheckedType:
    pass


def _check_type(result, expected):
    if expected is _UncheckedType:
        return True
    elif expected is None:
        return result is None
    else:
        return instance_check(result, expected)


class _TypeCheckedExpression:
    def __init__(self, expected_type: type | tuple = _UncheckedType):
        self._expected = expected_type

    def _checked(self, arg):
        assert _check_type(arg, self._expected), "invalid type in checked expression"
        return arg

    def __getitem__(self, expected_type):
        return type(self)(expected_type)


class _CheckType(_TypeCheckedExpression):
    def __call__(self, arg):
        assert (
            self._expected is not _UncheckedType
        ), "no type specified in std.check_type"
        return self._checked(arg)


class _Select(_TypeCheckedExpression):
    def __call__(self, arg, branches: dict, default=None):
        return self._checked(
            select_with(
                arg,
                branches,
                default=default,
            )
        )


def _first_impl(*args, default):
    if len(args) == 0:
        return default
    else:
        first, *rest = args
        return first[1] if first[0] else _first_impl(*rest, default=default)


class _ChooseFirst(_TypeCheckedExpression):
    def __call__(self, *args, default):
        return self._checked(_first_impl(*args, default=default))


class _Cond(_TypeCheckedExpression):
    def __call__(self, cond: bool, on_true, on_false):
        return self._checked(on_true if cond else on_false)


check_type = _CheckType()
select = _Select()
choose_first = _ChooseFirst()
cond = _Cond()


@_intrinsic
def _get_return_type_hint(fn):
    return typing.get_type_hints(fn).get("return", _UncheckedType)


def check_return(fn):
    if iscouroutinefunction(fn):

        async def wrapper(*args, **kwargs):
            result = await fn(*args, **kwargs)
            assert _check_type(
                result, _get_return_type_hint(fn)
            ), "invalid return value in function call"
            return result

    else:

        def wrapper(*args, **kwargs):
            result = fn(*args, **kwargs)
            assert _check_type(
                result, _get_return_type_hint(fn)
            ), "invalid return value in function call"
            return result

    wrapper.__name__ = fn.__name__
    return wrapper


#
#
#


def binary_fold(fn, first, *args):
    if len(args) == 0:
        return Temporary(first)
    else:
        return fn(first, binary_fold(fn, *args))


def concat(first, *args):
    return binary_fold(lambda a, b: a @ b, first, *args)


def stretch(val: Bit | BitVector, factor: int):
    if instance_check(val, Bit):
        return concat(*[val for _ in range(factor)])
    elif instance_check(val, BitVector):
        return concat(*[stretch(b, factor) for b in val])
    else:
        raise AssertionError("invalid argument")


def apply_mask(old: BitVector, new: BitVector, mask: BitVector):
    assert old.width == new.width
    return (old & ~mask) | (new & mask)
