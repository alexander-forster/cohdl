import cohdl
from cohdl import std
from cohdl import Port, Bit, Signal
import unittest


class WriteInputPort_concurrent(cohdl.Entity):
    sig_inp = Port.input(Bit)

    def architecture(self):
        @std.concurrent
        def logic():
            self.sig_inp <<= True


class WriteInputPort_sequential(cohdl.Entity):
    clk = Port.input(Bit)
    sig_inp = Port.input(Bit)

    def architecture(self):
        @std.sequential(std.Clock(self.clk))
        def logic():
            self.sig_inp <<= True


class SynthesizableTester(unittest.TestCase):
    def test_write_to_input_port(self):
        self.assertRaises(
            AssertionError, std.VhdlCompiler.to_string, WriteInputPort_concurrent
        )

        self.assertRaises(
            AssertionError, std.VhdlCompiler.to_string, WriteInputPort_sequential
        )
