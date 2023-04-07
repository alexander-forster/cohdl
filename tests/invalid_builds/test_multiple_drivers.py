import cohdl
from cohdl import std
from cohdl import Port, Bit, Signal, Variable
import unittest


class MultipleDrivers(cohdl.Entity):
    clk = Port.input(Bit)

    use_value = False
    first_read = False
    second_read = False
    first_seq = False
    second_seq = False

    def architecture(self):
        ctx_seq = std.sequential(std.Clock(self.clk))
        ctx_con = std.concurrent

        first_ctx = ctx_seq if self.first_seq else ctx_con
        second_ctx = ctx_seq if self.second_seq else ctx_con

        myvariable = Variable[Bit]()

        def read_var():
            x = Variable[Bit](myvariable)

        if self.use_value:

            def write_var():
                myvariable.value = True

        else:

            def write_var():
                nonlocal myvariable
                myvariable @= True

        first_fn = read_var if self.first_read else write_var
        second_fn = read_var if self.second_read else write_var

        @first_ctx
        def first():
            first_fn()

        @second_ctx
        def second():
            second_fn()


class SynthesizableTester(unittest.TestCase):
    def test_multiple_signal_drivers(self):
        for use_next in [True, False]:
            for first_read in [True, False]:
                for second_read in [True, False]:
                    for first_seq in [True, False]:
                        for second_seq in [True, False]:
                            MultipleDrivers.use_value = use_next
                            MultipleDrivers.first_read = first_read
                            MultipleDrivers.second_read = second_read
                            MultipleDrivers.first_seq = first_seq
                            MultipleDrivers.second_seq = second_seq

                            self.assertRaises(
                                AssertionError,
                                std.VhdlCompiler.to_string,
                                MultipleDrivers,
                            )
