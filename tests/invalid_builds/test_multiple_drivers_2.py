import cohdl
from cohdl import std
from cohdl import Port, Bit, BitVector
import unittest


def make_entity(first_seq, second_seq):
    class TestEntity(cohdl.Entity):
        clk = Port.input(Bit)
        result = Port.output(BitVector[8])

        def architecture(self):
            ctx_seq = std.sequential(std.Clock(self.clk))
            ctx_con = std.concurrent

            first_ctx = ctx_seq if first_seq else ctx_con
            second_ctx = ctx_seq if second_seq else ctx_con

            @first_ctx
            def first():
                self.result[0] <<= True

            @second_ctx
            def second():
                self.result[7] <<= False


class SynthesizableTester(unittest.TestCase):
    def test_multiple_signal_drivers(self):
        for first_seq in [True, False]:
            for second_seq in [True, False]:
                self.assertRaises(
                    AssertionError,
                    std.VhdlCompiler.to_string,
                    make_entity(first_seq, second_seq),
                )
