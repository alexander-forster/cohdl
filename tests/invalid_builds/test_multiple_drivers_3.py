import cohdl
from cohdl import std
from cohdl import Port, Bit, BitVector, Null
import unittest


def gen_entity(
    use_concurrent: bool,
    use_sequential: bool,
    use_always_fn_1: bool,
    use_always_block_1: bool,
    use_always_fn_2: bool,
    use_always_block_2: bool,
    set_elem: bool,
):
    class MultipleDrivers(cohdl.Entity):
        clk = Port.input(Bit)

        bit_inp = Port.input(Bit)

        vec_out = Port.output(BitVector[8], default=Null)

        def architecture(self):
            def assign():
                if set_elem:
                    self.vec_out[3] <<= Null
                else:
                    self.vec_out <<= Null

            if use_always_fn_1:

                @std.sequential
                def proc_always_fn_1():
                    cohdl.always(assign())

            if use_always_block_1:

                @std.sequential
                def proc_always_block_1():
                    with cohdl.always:
                        assign()

            if use_concurrent:

                @std.concurrent
                def logic():
                    assign()

            if use_sequential:

                @std.sequential
                def proc_seq():
                    assign()

            if use_always_fn_2:

                @std.sequential
                def proc_always_fn_2():
                    cohdl.always(assign())

            if use_always_block_2:

                @std.sequential
                def proc_always_block_2():
                    with cohdl.always:
                        assign()

    return MultipleDrivers


class SynthesizableTester(unittest.TestCase):
    # check, that multiple drivers are detected
    # when driving from always expressions/blocks
    def test_multiple_signal_drivers(self):
        import itertools

        for settings in itertools.product([True, False], repeat=6):
            driver_cnt = sum(settings)

            for set_elem in (True, False):
                entity = gen_entity(*settings, set_elem=set_elem)

                if driver_cnt > 1:
                    self.assertRaises(
                        AssertionError, std.VhdlCompiler.to_string, entity
                    )
                else:
                    std.VhdlCompiler.to_string(entity)
