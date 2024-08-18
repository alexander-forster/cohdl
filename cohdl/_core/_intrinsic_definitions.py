from ._intrinsic import _intrinsic, _intrinsic_replacement

from typing import TYPE_CHECKING
from types import NoneType

#
#
# intrinsic builtins
#
#

_intrinsic(getattr)
_intrinsic(hasattr)

_intrinsic(setattr)


@_intrinsic_replacement(setattr, special_case=False)
def setattr_replacement(__obj, __name, __value):
    assert hasattr(__obj, "_cohdl_init_active")
    setattr(__obj, __name, __value)


_intrinsic(min)
_intrinsic(max)
_intrinsic(abs)


@_intrinsic_replacement(min, special_case=False)
def min_replacement(*args):
    if len(args) == 1:
        args = args[0]

    assert all(isinstance(arg, (int, float, str)) for arg in args)
    return min(args)


@_intrinsic_replacement(max, special_case=False)
def max_replacement(*args):
    if len(args) == 1:
        args = args[0]

    assert all(isinstance(arg, (int, float, str)) for arg in args)
    return max(args)


@_intrinsic_replacement(abs, special_case=True, evaluate=True)
def abs_replacement(arg):
    return arg.__abs__()


#
# int methods
#

_intrinsic(int.__neg__)
_intrinsic(int.__pos__)
_intrinsic(int.__add__)
_intrinsic(int.__sub__)
_intrinsic(int.__mul__)
_intrinsic(int.__truediv__)
_intrinsic(int.__floordiv__)
_intrinsic(int.__mod__)
_intrinsic(int.__eq__)
_intrinsic(int.__ne__)
_intrinsic(int.__lt__)
_intrinsic(int.__gt__)
_intrinsic(int.__le__)
_intrinsic(int.__ge__)
_intrinsic(int.__bool__)
_intrinsic(int.__and__)
_intrinsic(int.__or__)
_intrinsic(int.__xor__)
_intrinsic(int.__pow__)
_intrinsic(int.__abs__)
_intrinsic(int.bit_count)
_intrinsic(int.bit_length)

#
# float methods
#


_intrinsic(float.__neg__)
_intrinsic(float.__pos__)
_intrinsic(float.__add__)
_intrinsic(float.__sub__)
_intrinsic(float.__mul__)
_intrinsic(float.__truediv__)
_intrinsic(float.__floordiv__)
_intrinsic(float.__mod__)
_intrinsic(float.__eq__)
_intrinsic(float.__ne__)
_intrinsic(float.__lt__)
_intrinsic(float.__gt__)
_intrinsic(float.__le__)
_intrinsic(float.__ge__)
_intrinsic(float.__bool__)
_intrinsic(float.__pow__)
_intrinsic(float.__abs__)

#
# bool methods
#

_intrinsic(bool.__eq__)
_intrinsic(bool.__ne__)
_intrinsic(bool.__bool__)
_intrinsic(bool.__and__)
_intrinsic(bool.__or__)
_intrinsic(bool.__xor__)

#
# dict methods
#

_intrinsic(dict)
_intrinsic(dict.items)
_intrinsic(dict.keys)
_intrinsic(dict.values)
_intrinsic(dict.get)
_intrinsic(dict.__getitem__)
_intrinsic(dict.__contains__)

#
# tuple methods
#

_intrinsic(tuple)
_intrinsic(tuple.__getitem__)


# indirect needed for case where tuples are merged
@_intrinsic_replacement(tuple.__getitem__, special_case=False)
def tuple_getitem_replacement(self, idx):
    return self.__getitem__(idx)


#
# list methods
#

_intrinsic(list)
_intrinsic(list.__getitem__)
_intrinsic(list.__add__)
_intrinsic(list.__mul__)
_intrinsic(list.__rmul__)


# indirect needed for case where lists are merged
@_intrinsic_replacement(list.__getitem__, special_case=False)
def list_getitem_replacement(self, idx):
    return self.__getitem__(idx)


#
# str methods
#

_intrinsic(str.__eq__)
_intrinsic(str.__len__)
_intrinsic(str.format)

#
# slice methods
#

_intrinsic(slice)

#
# object methods
#

_intrinsic(object.__new__)
_intrinsic(type(object).__new__)
_intrinsic(object.__eq__)
_intrinsic(object.__ne__)

#
# type methods
#

_intrinsic(type.__or__)
_intrinsic(type.__ror__)

#
# None methods
#


_intrinsic(NoneType.__bool__)
_intrinsic(NoneType.__eq__)


#
# range
#

_intrinsic(range)


#
#
#

_intrinsic(zip)
_intrinsic(enumerate)
_intrinsic(len)

# allows static print during synthesis
_intrinsic(print)

#
# all
#

_intrinsic(all)


@_intrinsic_replacement(all)
def all_replacemet(iterable, /):
    return _All(iterable)


class _All:
    def __init__(self, iterable):
        self.iterable = iterable


#
# any
#

_intrinsic(any)


@_intrinsic_replacement(any)
def any_replacement(iterable, /):
    return _Any(iterable)


class _Any:
    def __init__(self, iterable):
        self.iterable = iterable


#
# bool
#

_intrinsic(bool)


@_intrinsic_replacement(bool)
def bool_replacement(value, /):
    return _Bool(value)


class _Bool:
    def __init__(self, value):
        self.value = value


#
# always
#


class _Always:
    def __call__(self, expr, /):
        raise AssertionError("always called outside synthesizable context")

    def __enter__(self):
        return self

    def __exit__(self, a, b, c):
        pass


always = _Always()


#
# expr
#

_expr_functions = {}


@_intrinsic
def _is_expr_function(fn):
    return id(fn) in _expr_functions


def expr(e, /):
    # should never be called, expr is handled by the parser

    raise AssertionError("expr called outside synthesizable context")


@_intrinsic
def expr_fn(e, /):
    _expr_functions[id(e)] = e
    return e


#
# evaluated
#


@_intrinsic
def evaluated():
    return False


@_intrinsic_replacement(evaluated, special_case=False)
def evaluated_replacement():
    return True


#
# static assert
#


@_intrinsic
def static_assert(cond: bool, msg: str | None = None):
    if msg is None:
        assert cond
    else:
        assert cond, msg
