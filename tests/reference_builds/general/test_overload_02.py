from __future__ import annotations

import unittest

import cohdl
from cohdl import BitVector, Unsigned, Port
from cohdl import std

import itertools
from cohdl_testutil import cocotb_util


class TestComplex:
    def __init__(self, real, imag):
        self.real = real
        self.imag = imag

    def __radd__(self, other):
        if isinstance(other, int):
            return TestComplex(other + self.real, self.imag)
        else:
            return TestComplex(other.real + self.real, self.imag)

    def __rsub__(self, other):
        if isinstance(other, int):
            return TestComplex(other - self.real, self.imag)
        else:
            return TestComplex(other.real - self.real, self.imag)


class test_overload_02(cohdl.Entity):
    a_real = Port.input(Unsigned[3])
    a_imag = Port.input(Unsigned[3])
    b_real = Port.input(Unsigned[3])
    b_imag = Port.input(Unsigned[3])

    sum_real = Port.output(Unsigned[3])
    sum_imag = Port.output(Unsigned[3])

    dif_real = Port.output(Unsigned[3])
    dif_imag = Port.output(Unsigned[3])

    def architecture(self):
        a = TestComplex(self.a_real, self.a_imag)
        b = TestComplex(self.b_real, self.b_imag)

        @std.concurrent
        def logic():
            x_sum = 1 + b
            x_dif = 1 - b

            self.sum_real <<= x_sum.real
            self.sum_imag <<= x_sum.imag

            self.dif_real <<= x_dif.real
            self.dif_imag <<= x_dif.imag


#
# test code
#


@cocotb_util.test()
async def testbench_overload_02(dut: test_overload_02):
    inp_gen = cocotb_util.ConstrainedGenerator(3)

    for a_real, a_imag, b_real, b_imag in itertools.product(
        inp_gen.all(), inp_gen.all(), inp_gen.all(), inp_gen.all()
    ):
        a = TestComplex(a_real, a_imag)
        b = TestComplex(b_real, b_imag)

        sum = 1 + b
        dif = 1 - b

        await cocotb_util.check_concurrent(
            [
                (dut.a_real, a_real),
                (dut.a_imag, a_imag),
                (dut.b_real, b_real),
                (dut.b_imag, b_imag),
            ],
            [
                (dut.sum_real, sum.real),
                (dut.sum_imag, sum.imag),
                (dut.dif_real, dif.real),
                (dut.dif_imag, dif.imag),
            ],
        )


class Unittest(unittest.TestCase):
    def test_overload_02(self):
        cocotb_util.run_cocotb_tests(test_overload_02, __file__, self.__module__)
