import cohdl
from cohdl import std
from cohdl import Port, Bit, Signal, Variable, BitVector, Unsigned
import unittest


class VariableInConcurrent_1(cohdl.Entity):
    x = Port.output(Bit)

    def architecture(self):
        v = Variable[Bit]()

        @std.concurrent
        def proc():
            self.x <<= v


class VariableInConcurrent_2(cohdl.Entity):
    x = Port.output(Bit)
    y = Port.input(Bit)

    def architecture(self):
        v = Variable[Bit]()

        @std.concurrent
        def proc():
            v.value = self.y
            self.x <<= self.y


class VariableInConcurrent_3(cohdl.Entity):
    x = Port.output(Bit)
    y = Port.input(BitVector[4])

    def architecture(self):
        v = Variable[Unsigned[2]]()

        @std.concurrent
        def proc():
            self.x <<= self.y[v]


class SynthesizableTester(unittest.TestCase):
    def test_variable_in_concurrent(self):

        self.assertRaises(
            AssertionError,
            std.VhdlCompiler._to_ir,
            VariableInConcurrent_1,
        )

        self.assertRaises(
            AssertionError,
            std.VhdlCompiler._to_ir,
            VariableInConcurrent_2,
        )

        self.assertRaises(
            AssertionError,
            std.VhdlCompiler._to_ir,
            VariableInConcurrent_3,
        )
