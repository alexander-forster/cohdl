import cohdl
from cohdl import std
from cohdl import Port, Bit, BitVector, Signal
import unittest


class ExtEntity(cohdl.Entity, extern=True):
    a = Port.input(Bit)


class TopEntity(cohdl.Entity):
    inp = Port.input(BitVector[4])

    def architecture(self):
        ExtEntity(a=self.inp)


class SynthesizableTester(unittest.TestCase):
    def test_incompatible_entity_port(self):
        self.assertRaises(AssertionError, std.VhdlCompiler.to_string, TopEntity)
