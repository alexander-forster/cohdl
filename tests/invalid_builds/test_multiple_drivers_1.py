import cohdl
from cohdl import std
from cohdl import Port, Bit, Signal, Variable
import unittest


def gen_entity(
    use_value=False,
    first_read=False,
    second_read=False,
    first_seq=False,
    second_seq=False,
):
    class MultipleDrivers(cohdl.Entity):
        clk = Port.input(Bit)

        def architecture(self):
            ctx_seq = std.sequential(std.Clock(self.clk))
            ctx_con = std.concurrent

            first_ctx = ctx_seq if first_seq else ctx_con
            second_ctx = ctx_seq if second_seq else ctx_con

            myvariable = Variable[Bit]()

            def read_var():
                x = Variable[Bit](myvariable)

            if use_value:

                def write_var():
                    myvariable.value = True

            else:

                def write_var():
                    nonlocal myvariable
                    myvariable @= True

            first_fn = read_var if first_read else write_var
            second_fn = read_var if second_read else write_var

            @first_ctx
            def first():
                first_fn()

            @second_ctx
            def second():
                second_fn()

    return MultipleDrivers


class SynthesizableTester(unittest.TestCase):
    def test_multiple_signal_drivers(self):
        for use_next in [True, False]:
            for first_read in [True, False]:
                for second_read in [True, False]:
                    for first_seq in [True, False]:
                        for second_seq in [True, False]:
                            self.assertRaises(
                                AssertionError,
                                std.VhdlCompiler.to_string,
                                gen_entity(
                                    use_value=use_next,
                                    first_read=first_read,
                                    second_read=second_read,
                                    first_seq=first_seq,
                                    second_seq=second_seq,
                                ),
                            )
