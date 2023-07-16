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


def fn_b(a=None):
    return ArgWrapper([a])


def fn_c(a, b=5678):
    return ArgWrapper([a, b])


def fn_d(a=1, b=2, c=3):
    return ArgWrapper([a, b, c])


def fn_e(*, a=643):
    return ArgWrapper([a])


def fn_f(a=123, *, b):
    return ArgWrapper([a, b])


def fn_g(a=4.567, *, b=675, c):
    return ArgWrapper([a, b, c])


def fn_h(a, /, b=432, *, c):
    return ArgWrapper([a, b, c])


def fn_i(a=5, /, *b, c="asdfsad"):
    return ArgWrapper([a, c], varargs=b)


def fn_j(a=6.321, /, *b, c=None, **d):
    return ArgWrapper([a, c], varargs=b, kwargs=d)


class test_call_02(cohdl.Entity):
    def architecture(self):
        def run_functions():
            return [
                fn_a(),
                #
                fn_b(0),
                fn_b(),
                #
                fn_c(1),
                fn_c(1, b=3.4),
                #
                fn_d(),
                fn_d(3),
                fn_d(3, 2),
                fn_d(3, 2, 1),
                fn_d(4, 5, c=6),
                fn_d(4, c=6),
                fn_d(44, b=21),
                fn_d(a=1),
                fn_d(b=7),
                fn_d(c=4),
                fn_d(*[9.0, 9.2]),
                fn_d(**{"b": "12213"}),
                #
                fn_e(),
                fn_e(a=55),
                fn_e(**{"a": 66}),
                fn_e(),
                fn_e(**{}),
                #
                fn_f(b=200),
                fn_f(100, b=31),
                fn_g(
                    c=222,
                ),
                fn_h(0, c=3),
                fn_h(0, c=3, b=4),
                fn_i(),
                fn_i(0, 1, 2, 3, 4, 5, 6),
                fn_i(2, 4, 6, *[1, 1, 1], *[2, 2]),
                fn_i(3),
                #
                fn_j(),
                fn_j(11, 12, c=13, a=14),
                fn_j(10, 12, **{"x": 342}),
                fn_j(10, 11, **{"b": 342, "a": 55}),
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
    def test_call_02(self):
        std.VhdlCompiler.to_string(test_call_02)
