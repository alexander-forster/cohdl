import cohdl
from cohdl import std
from cohdl import Port, Bit, BitVector, Null
import unittest


def gen_entity(
    use_concurrent: bool,
    use_sequential: bool,
    use_entity_a: bool,
    use_entity_b: bool,
    use_entity_seq: bool,
    use_entity_concurrent: bool,
    ext_entity: bool,
):
    if ext_entity:

        class SubEntity(cohdl.Entity, external=True):
            port_inp = Port.input(BitVector[4])
            port_out = Port.output(BitVector[4])

    else:

        class SubEntity(cohdl.Entity):
            port_inp = Port.input(BitVector[4])
            port_out = Port.output(BitVector[4])

            def architecture(self):
                std.concurrent_assign(self.port_out, self.port_inp)

    class MultipleDrivers(cohdl.Entity):
        clk = Port.input(Bit)

        vec_inp = Port.input(BitVector[4])
        vec_out = Port.output(BitVector[8], default=Null)

        def architecture(self):
            if use_entity_a:
                SubEntity(port_inp=self.vec_inp, port_out=self.vec_out[4:1])

            if use_concurrent:

                @std.concurrent
                def logic():
                    self.vec_out[0] <<= True

            if use_sequential:

                @std.sequential
                def proc_seq():
                    self.vec_out[1] <<= False

            if use_entity_seq:

                @std.sequential
                def proc_seq_entity():
                    cohdl.always(
                        SubEntity(port_inp=self.vec_inp, port_out=self.vec_out[6:3])
                    )

            if use_entity_concurrent:

                @std.concurrent
                def proc_seq_entity():
                    SubEntity(port_inp=self.vec_inp, port_out=self.vec_out[7:4])

            if use_entity_b:
                SubEntity(port_inp=self.vec_inp, port_out=self.vec_out[3:0])

    return MultipleDrivers


class SynthesizableTester(unittest.TestCase):
    # check, that multiple drivers are detected
    # when driving from entities
    def test_multiple_signal_drivers(self):
        import itertools

        for settings in itertools.product([True, False], repeat=6):
            driver_cnt = sum(settings)

            for ext_entity in (True, False):
                entity = gen_entity(*settings, ext_entity=ext_entity)

                if driver_cnt > 1:
                    self.assertRaises(
                        AssertionError, std.VhdlCompiler.to_string, entity
                    )
                else:
                    std.VhdlCompiler.to_string(entity)
