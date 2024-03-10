from cohdl import Bit, Signal
from cohdl import vhdl as raw_vhdl

from cohdl import pyeval, Attribute

import enum


class CmpType(enum.Enum):
    ID = enum.auto()
    EQ = enum.auto()


class Cache:
    def __init__(self, arg_types):
        self._arg_types = arg_types
        self._entries = []

    @pyeval
    def lookup(self, args):
        assert len(args) == len(self._arg_types)

        for cached_value, cached_args in self._entries:
            for cmp_type, arg, cached in zip(self._arg_types, args, cached_args):
                if cmp_type is CmpType.ID and arg is not cached:
                    break
                elif arg != cached:
                    break
            else:
                return (True, cached_value)

        return (False, None)

    @pyeval
    def add_entry(self, value, args):
        assert len(args) == len(self._arg_types)
        self._entries.append((value, args))


@pyeval
def cached(*cmp_types):
    cache = Cache(cmp_types)

    def helper(fn):
        def wrapped(*args):
            found, value = cache.lookup(args)

            if found:
                return value
            else:
                new_entry = fn(*args)
                cache.add_entry(new_entry, args)
                return new_entry

        return wrapped

    return helper


class vhdl(raw_vhdl):
    def post_process(self, text: str):
        result = text.replace("<%", "{")
        return result.replace("%>", "}")


#
# attributes
#


class anyconst(Attribute, type=bool): ...


@cached(CmpType.ID)
def stable(arg):
    return f"{vhdl[bool]:stable({arg!r})}"


@cached(CmpType.ID, CmpType.EQ)
def _cached_prev(sig, cnt):
    if cnt is None:
        return f"{vhdl[sig.type]:prev({sig!r})}"
    else:
        return f"{vhdl[sig.type]:prev({sig!r}, {cnt})}"


def prev(sig, cnt=None):
    return _cached_prev(sig, cnt)


#
#
#


def _n_prev_true(sig, n: int):
    if n == 0:
        return sig
    else:
        return sig and _n_prev_true(prev(sig), n - 1)


def n_prev_true(sig, n: int | tuple):
    if isinstance(n, int):
        return _n_prev_true(sig, n)
    else:
        min_n, max_n = n
        return _n_prev_true(sig, min_n) and not prev(sig, max_n + 1)
