from __future__ import annotations

import unittest

import cohdl
from cohdl import std, Unsigned, Port, Bit, BitVector, Null, Full

from cohdl_testutil import cocotb_util


class test_qualifiers(cohdl.Entity):

    inp_bit = Port.input(Bit)
    inp_bitvector = Port.input(BitVector[5])

    chosen_a = Port.output(Bit)
    chosen_b = Port.output(Unsigned[5])
    chosen_c = Port.output(BitVector[5])

    def architecture(self):

        def check_qualifiers(inp):
            assert inp is std.Ref(inp)

            sig = std.Signal(inp)
            assert isinstance(sig, std.Signal)
            assert sig.type is inp.type
            assert sig == inp

            var = std.Variable(inp)
            assert isinstance(var, std.Variable)
            assert var.type is inp.type
            assert var == inp

            temp = std.Temporary(inp)
            assert isinstance(temp, std.Temporary)
            assert temp.type is inp.type
            assert temp == inp

            val = std.Value(inp)
            assert isinstance(val, std.Temporary)
            assert val.type is inp.type
            assert val == inp

        def check_container(cont):
            def check_ref(a, b):
                if isinstance(a, (tuple, list)):
                    assert type(a) is type(b), "type is not same"

                    for x, y in zip(a, b, strict=True):
                        check_ref(x, y)
                else:
                    assert a is b, "value is not same"

            check_ref(cont, std.Ref(cont))

            def check_qualifier(a, b, qual):
                if isinstance(a, (tuple, list)):
                    assert type(a) is type(b), "type is not same"

                    for x, y in zip(a, b, strict=True):
                        check_qualifier(x, y, qual)
                else:
                    assert isinstance(b, qual)
                    assert a.type is b.type
                    assert a == b

            check_qualifier(cont, std.Signal(cont), std.Signal)
            check_qualifier(cont, std.Variable(cont), std.Variable)
            check_qualifier(cont, std.Temporary(cont), std.Temporary)
            check_qualifier(cont, std.Value(cont), std.Temporary)

        @cohdl.sequential_context
        def logic():
            check_qualifiers(self.inp_bit)

            check_container((self.inp_bit, self.inp_bit))
            check_container([self.inp_bit, self.inp_bit])

            check_container((self.inp_bit, self.inp_bit, self.inp_bitvector))
            check_container([self.inp_bit, self.inp_bit, self.inp_bitvector])

            check_container(
                (self.inp_bitvector.unsigned, (self.inp_bitvector[3], self.inp_bit, []))
            )
            check_container(
                [self.inp_bitvector.unsigned, (self.inp_bitvector[3], self.inp_bit, [])]
            )

            option_a = (self.inp_bit, self.inp_bitvector[1:0].unsigned, Null)
            option_b = (
                self.inp_bit,
                self.inp_bitvector[2:0].unsigned,
                self.inp_bitvector,
            )

            choice = option_a if self.inp_bitvector[2] else option_b
            a, b, c = choice

            assert a is choice[0]
            assert b is choice[1]
            assert c is choice[2]

            self.chosen_a <<= choice[0]
            self.chosen_b <<= choice[1]
            self.chosen_c <<= c


# print(std.VhdlCompiler.to_string(test_qualifiers))
# exit()

#
# test code
#


@cocotb_util.test()
async def testbench_qualifiers(dut: test_qualifiers):
    gen = cocotb_util.ConstrainedGenerator(8)

    for nr in range(256):
        bit = nr % 2
        vec = nr % 30

        dut.inp_bit.value = bit
        dut.inp_bitvector.value = vec
        await cocotb_util.step()

        assert dut.chosen_a == bit
        assert dut.chosen_b == (vec % 4 if vec & 0b100 else vec % 8)
        assert dut.chosen_c == (0 if vec & 0b100 else vec)


class Unittest(unittest.TestCase):
    def test_hdl(self):
        cocotb_util.run_cocotb_tests(test_qualifiers, __file__, self.__module__)
