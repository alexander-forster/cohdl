from __future__ import annotations

import unittest

import cohdl
from cohdl import Port
from cohdl import std

from cohdl_testutil import cocotb_util


class TestValue:
    def __init__(self, val):
        self.val = val

    def __getitem__(self, index):
        return self.val

    def __add__(self, x):
        return self.val + x

    def __radd__(self, x):
        return x + self.val

    def __sub__(self, x):
        return self.val - x

    def __rsub__(self, x):
        return x - self.val

    def __mul__(self, x):
        return self.val * x

    def __rmul__(self, x):
        return x * self.val

    def __matmul__(self, x):
        return self.val @ x

    def __rmatmul__(self, x):
        return x @ self.val

    def __truediv__(self, x):
        return self.val / x

    def __rtruediv__(self, x):
        return x / self.val

    def __floordiv__(self, x):
        return self.val // x

    def __rfloordiv__(self, x):
        return x // self.val

    def __mod__(self, x):
        return self.val % x

    def __rmod__(self, x):
        return x % self.val

    def __pow__(self, x):
        return self.val**x

    def __rpow__(self, x):
        return x**self.val

    def __and__(self, x):
        return self.val & x

    def __rand__(self, x):
        return x & self.val

    def __or__(self, x):
        return x | self.val

    def __ror__(self, x):
        return self.val | x

    def __xor__(self, x):
        return self.val ^ x

    def __rxor__(self, x):
        return x ^ self.val


class MatmulValue:
    def __init__(self, val):
        self.val = val

    def __matmul__(self, x):
        return self.val * 1000 + x

    def __rmatmul__(self, x):
        return x * 1000 + self.val


class test_overload_03(cohdl.Entity):
    a = Port.input(cohdl.Bit)
    b = Port.output(cohdl.Bit)

    def architecture(self):
        @cohdl.consteval
        def static_check(value, expected):
            assert isinstance(value, int)
            assert isinstance(expected, int)
            assert value == expected, f"{value} != {expected}"

        @cohdl.consteval
        def static_check_float(value, expected):
            assert isinstance(value, float)
            assert isinstance(expected, float)
            assert value == expected, f"{value} != {expected}"

        val_0 = TestValue(0)
        val_1 = TestValue(1)

        val_matmul = MatmulValue(123)

        @std.concurrent
        def logic():
            self.b <<= self.a

            val_100 = TestValue(100)

            static_check(val_0 + 1, 1)
            static_check(1 + val_0, 1)

            static_check(val_0 - 1, -1)
            static_check(1 - val_0, 1)

            static_check(val_0 * 1, 0)
            static_check(1 * val_1, 1)

            static_check(val_1 // 1, 1)
            static_check(123 // val_1, 123)

            static_check(val_100 % 90, 10)
            static_check(111 % val_100, 11)

            static_check(val_1 & 3, 1)
            static_check(3 & val_1, 1)

            static_check(val_100 | 1, 101)
            static_check(1 | val_100, 101)

            static_check(val_1**4, 1)
            static_check(4**val_1, 4)

            static_check_float(4 / val_1, 4.0)
            static_check_float(val_100 / 20, 5.0)

            static_check(val_matmul @ 1, 123001)
            static_check(321 @ val_matmul, 321123)


#
# test code
#


@cocotb_util.test()
async def testbench_overload_03(dut: test_overload_03):
    await cocotb_util.step()


class Unittest(unittest.TestCase):
    def test_overload_03(self):
        cocotb_util.run_cocotb_tests(test_overload_03, __file__, self.__module__)
