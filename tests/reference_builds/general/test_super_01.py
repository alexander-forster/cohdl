from __future__ import annotations

import unittest

import cohdl
from cohdl import BitVector, Port
from cohdl import std

import itertools
from cohdl_testutil import cocotb_util


class Wrapper:
    def __init__(self, a, b, c):
        self.a = a
        self.b = b
        self.c = c

    def and_all(self):
        return self.a & self.b & self.c

    def or_all(self):
        return self.a | self.b | self.c

    def xor_all(self):
        return self.a ^ self.b ^ self.c

    def operation(self):
        return self.a ^ self.b & self.c


class Derived(Wrapper):
    def __init__(self, a, b, c):
        super().__init__(a, b, c)

    def xor_all(self):
        return super().xor_all()

    def operation(self):
        return self.a | self.b & self.c


class test_class_01(cohdl.Entity):
    inp1 = Port.input(BitVector[4])
    inp2 = Port.input(BitVector[4])
    inp3 = Port.input(BitVector[4])

    out1 = Port.output(BitVector[4])
    out2 = Port.output(BitVector[4])
    out3 = Port.output(BitVector[4])
    out4 = Port.output(BitVector[4])

    def architecture(self):
        @std.concurrent
        def logic():
            derived = Derived(self.inp1, self.inp2, self.inp3)
            self.out1 <<= derived.and_all()
            self.out2 <<= derived.or_all()
            self.out3 <<= derived.xor_all()
            self.out4 <<= derived.operation()


#
# test code
#


@cocotb_util.test()
async def testbench_class_01(dut: test_class_01):
    inp_gen = cocotb_util.ConstrainedGenerator(4)

    for inp1, inp2, inp3 in itertools.product(
        inp_gen.all(), inp_gen.all(), inp_gen.all()
    ):
        await cocotb_util.check_concurrent(
            [(dut.inp1, inp1), (dut.inp2, inp2), (dut.inp3, inp3)],
            [
                (dut.out1, inp1 & inp2 & inp3),
                (dut.out2, inp1 | inp2 | inp3),
                (dut.out3, inp1 ^ inp2 ^ inp3),
                (dut.out4, inp1 | inp2 & inp3),
            ],
        )


class Unittest(unittest.TestCase):
    def test_class_01(self):
        cocotb_util.run_cocotb_tests(test_class_01, __file__, self.__module__)
