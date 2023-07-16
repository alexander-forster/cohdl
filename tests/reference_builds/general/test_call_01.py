from __future__ import annotations

import unittest

import cohdl
from cohdl import std


class ArgWrapper:
    def __init__(self, args, varargs=None, kwargs=None):
        self.args = args
        self.varargs = varargs
        self.kwargs = kwargs

    @cohdl.consteval
    def check(self, expected: ArgWrapper):
        assert self.args == expected.args and self.varargs == expected.varargs, (
            self.kwargs == expected.kwargs
        )


def fn_a():
    return ArgWrapper([])


def fn_b(a):
    return ArgWrapper([a])


def fn_c(a, b):
    return ArgWrapper([a, b])


def fn_d(a, b, c):
    return ArgWrapper([a, b, c])


def fn_e(*, a):
    return ArgWrapper([a])


def fn_f(a, *, b):
    return ArgWrapper([a, b])


def fn_g(a, *, b, c):
    return ArgWrapper([a, b, c])


def fn_h(a, /, b, *, c):
    return ArgWrapper([a, b, c])


def fn_i(a, /, *b, c):
    return ArgWrapper([a, c], varargs=b)


def fn_j(a, /, *b, c, **d):
    return ArgWrapper([a, c], varargs=b, kwargs=d)


class test_call_01(cohdl.Entity):
    def architecture(self):
        def run_functions():
            return [
                fn_a(),
                #
                fn_b(0),
                fn_b(None),
                fn_b(a="asdf"),
                #
                fn_c(1, 2),
                fn_c(1, b=3.4),
                fn_c(a=3, b=-1),
                fn_c(*[0.1, 5]),
                fn_c(**{"a": 9, "b": 11}),
                #
                fn_d(3, 2, 1),
                fn_d(4, 5, c=6),
                fn_d(b=7, c=8, a=9),
                fn_d(*[9.0, 9.1, 9.2]),
                #
                fn_e(a=55),
                fn_e(**{"a": 66}),
                #
                fn_f(100, b=200),
                fn_g(111, c=222, b=333),
                fn_h(0, 1, c=3),
                fn_h(0, c=3, b=4),
                #
                fn_i(0, 1, 2, 3, 4, 5, 6, c=7),
                fn_i(2, 4, 6, *[1, 1, 1], *[2, 2], c=9),
                fn_i(3, c=4),
                #
                fn_j(10, 11, 12, c=13),
                fn_j(10, 11, 12, c=13, a=14),
                fn_j(10, 11, 12, **{"c": "14", "x": 342}),
                fn_j(10, 11, 12, **{"c": "14", "b": 342, "a": 55}),
            ]

        @cohdl.consteval
        def check_result(result):
            expected = run_functions()

            assert len(result) == len(expected)

            for r, e in zip(result, expected):
                r.check(e)

        @std.concurrent
        def logic():
            result = run_functions()
            check_result(result)


#
# test code
#


class Unittest(unittest.TestCase):
    def test_call_01(self):
        std.VhdlCompiler.to_string(test_call_01)
