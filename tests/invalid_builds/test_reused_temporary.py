import cohdl
from cohdl import std
from cohdl import Port, Bit, true
import unittest


class test_reused_temporary(cohdl.Entity):
    clk = Port.input(Bit)
    sig_inp = Port.input(Bit)
    sig_out = Port.output(Bit)

    def architecture(self):
        @std.sequential(std.Clock(self.clk))
        async def proc():
            my_temp = self.sig_inp | self.sig_inp
            await true
            # temporaries can only be used in
            # the state they were generated in
            self.sig_out <<= my_temp


class SynthesizableTester(unittest.TestCase):
    def test_write_to_input_port(self):
        self.assertRaises(
            AssertionError, std.VhdlCompiler.to_string, test_reused_temporary
        )
