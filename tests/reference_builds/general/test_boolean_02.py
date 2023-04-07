from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Unsigned, Signed, Signal, true, false

from cohdl import std

from cohdl_testutil import cocotb_util

gen = cocotb_util.ConstrainedGenerator


class test_boolean_02(cohdl.Entity):
    input_bit = Port.input(Bit)
    input_bool = Port.input(bool)
    input_bitvector = Port.input(BitVector[3])
    input_unsigned = Port.input(Unsigned[3])
    input_signed = Port.input(Signed[3])

    output_test_bit = Port.output(bool)
    output_test_bool = Port.output(bool)
    output_test_bitvector = Port.output(bool)
    output_test_unsigned = Port.output(bool)
    output_test_signed = Port.output(bool)
    output_test_int = Port.output(bool)

    output_not_bit = Port.output(bool)
    output_not_bool = Port.output(bool)
    output_not_bitvector = Port.output(bool)
    output_not_unsigned = Port.output(bool)
    output_not_signed = Port.output(bool)
    output_not_int = Port.output(bool)

    output_bit_and_bit = Port.output(bool)
    output_bit_and_bool = Port.output(bool)
    output_bool_and_bit = Port.output(bool)
    output_bool_and_bool = Port.output(bool)
    output_bit_and_bv = Port.output(bool)
    output_bv_and_bit = Port.output(bool)
    output_bool_and_bv = Port.output(bool)
    output_bv_and_bool = Port.output(bool)
    output_bv_and_bv = Port.output(bool)

    output_bit_and_not_bit = Port.output(bool)
    output_bit_and_not_bool = Port.output(bool)
    output_bool_and_not_bit = Port.output(bool)
    output_bool_and_not_bool = Port.output(bool)
    output_bit_and_not_bv = Port.output(bool)
    output_bv_and_not_bit = Port.output(bool)
    output_bool_and_not_bv = Port.output(bool)
    output_bv_and_not_bool = Port.output(bool)
    output_bv_and_not_bv = Port.output(bool)

    output_not_bit_and_bit = Port.output(bool)
    output_not_bit_and_bool = Port.output(bool)
    output_not_bool_and_bit = Port.output(bool)
    output_not_bool_and_bool = Port.output(bool)
    output_not_bit_and_bv = Port.output(bool)
    output_not_bv_and_bit = Port.output(bool)
    output_not_bool_and_bv = Port.output(bool)
    output_not_bv_and_bool = Port.output(bool)
    output_not_bv_and_bv = Port.output(bool)

    output_bit_or_bit = Port.output(bool)
    output_bit_or_bool = Port.output(bool)
    output_bool_or_bit = Port.output(bool)
    output_bool_or_bool = Port.output(bool)
    output_bit_or_bv = Port.output(bool)
    output_bv_or_bit = Port.output(bool)
    output_bool_or_bv = Port.output(bool)
    output_bv_or_bool = Port.output(bool)
    output_bv_or_bv = Port.output(bool)

    output_bit_or_not_bit = Port.output(bool)
    output_bit_or_not_bool = Port.output(bool)
    output_bool_or_not_bit = Port.output(bool)
    output_bool_or_not_bool = Port.output(bool)
    output_bit_or_not_bv = Port.output(bool)
    output_bv_or_not_bit = Port.output(bool)
    output_bool_or_not_bv = Port.output(bool)
    output_bv_or_not_bool = Port.output(bool)
    output_bv_or_not_bv = Port.output(bool)

    output_not_bit_or_bit = Port.output(bool)
    output_not_bit_or_bool = Port.output(bool)
    output_not_bool_or_bit = Port.output(bool)
    output_not_bool_or_bool = Port.output(bool)
    output_not_bit_or_bv = Port.output(bool)
    output_not_bv_or_bit = Port.output(bool)
    output_not_bool_or_bv = Port.output(bool)
    output_not_bv_or_bool = Port.output(bool)
    output_not_bv_or_bv = Port.output(bool)

    output_complex_a = Port.output(bool)
    output_complex_b = Port.output(bool)
    output_complex_c = Port.output(bool)
    output_complex_d = Port.output(bool)
    output_complex_e = Port.output(bool)

    def architecture(self):
        integer = Signal[int]()

        @std.concurrent
        def logic_simple():
            nonlocal integer
            integer <<= self.input_unsigned

            # complex expressions

            self.output_complex_a <<= self.input_bit and self.input_bool or not integer
            self.output_complex_b <<= not not not not not self.input_bit
            self.output_complex_c <<= not not (
                not (not not not self.input_bit and self.input_bool) or not not integer
            )
            self.output_complex_d <<= self.input_bit and true or self.input_bitvector
            self.output_complex_e <<= self.input_bit or false or self.input_bitvector

            # bool(X)
            self.output_test_bit <<= bool(self.input_bit)
            self.output_test_bool <<= bool(self.input_bool)
            self.output_test_bitvector <<= bool(self.input_bitvector)
            self.output_test_unsigned <<= bool(self.input_unsigned)
            self.output_test_signed <<= bool(self.input_signed)
            self.output_test_int <<= bool(integer)

            # not X
            self.output_not_bit <<= not self.input_bit
            self.output_not_bool <<= not self.input_bool
            self.output_not_bitvector <<= not self.input_bitvector
            self.output_not_unsigned <<= not self.input_unsigned
            self.output_not_signed <<= not self.input_signed
            self.output_not_int <<= not integer

            # A and B
            self.output_bit_and_bit <<= self.input_bit and self.input_bit
            self.output_bit_and_bool <<= self.input_bit and self.input_bool
            self.output_bool_and_bit <<= self.input_bool and self.input_bit
            self.output_bool_and_bool <<= self.input_bool and self.input_bool
            self.output_bit_and_bv <<= self.input_bit and self.input_bitvector
            self.output_bv_and_bit <<= self.input_bitvector and self.input_bit
            self.output_bool_and_bv <<= self.input_bool and self.input_bitvector
            self.output_bv_and_bool <<= self.input_bitvector and self.input_bool
            self.output_bv_and_bv <<= self.input_bitvector and self.input_bitvector
            # A and not B
            self.output_bit_and_not_bit <<= self.input_bit and not self.input_bit
            self.output_bit_and_not_bool <<= self.input_bit and not self.input_bool
            self.output_bool_and_not_bit <<= self.input_bool and not self.input_bit
            self.output_bool_and_not_bool <<= self.input_bool and not self.input_bool
            self.output_bit_and_not_bv <<= self.input_bit and not self.input_bitvector
            self.output_bv_and_not_bit <<= self.input_bitvector and not self.input_bit
            self.output_bool_and_not_bv <<= self.input_bool and not self.input_bitvector
            self.output_bv_and_not_bool <<= self.input_bitvector and not self.input_bool
            self.output_bv_and_not_bv <<= (
                self.input_bitvector and not self.input_bitvector
            )
            # not A and B
            self.output_not_bit_and_bit <<= not self.input_bit and self.input_bit
            self.output_not_bit_and_bool <<= not self.input_bit and self.input_bool
            self.output_not_bool_and_bit <<= not self.input_bool and self.input_bit
            self.output_not_bool_and_bool <<= not self.input_bool and self.input_bool
            self.output_not_bit_and_bv <<= not self.input_bit and self.input_bitvector
            self.output_not_bv_and_bit <<= not self.input_bitvector and self.input_bit
            self.output_not_bool_and_bv <<= not self.input_bool and self.input_bitvector
            self.output_not_bv_and_bool <<= not self.input_bitvector and self.input_bool
            self.output_not_bv_and_bv <<= (
                not self.input_bitvector and self.input_bitvector
            )

            #
            #
            #

            # A or B
            self.output_bit_or_bit <<= self.input_bit or self.input_bit
            self.output_bit_or_bool <<= self.input_bit or self.input_bool
            self.output_bool_or_bit <<= self.input_bool or self.input_bit
            self.output_bool_or_bool <<= self.input_bool or self.input_bool
            self.output_bit_or_bv <<= self.input_bit or self.input_bitvector
            self.output_bv_or_bit <<= self.input_bitvector or self.input_bit
            self.output_bool_or_bv <<= self.input_bool or self.input_bitvector
            self.output_bv_or_bool <<= self.input_bitvector or self.input_bool
            self.output_bv_or_bv <<= self.input_bitvector or self.input_bitvector
            # A or not B
            self.output_bit_or_not_bit <<= self.input_bit or not self.input_bit
            self.output_bit_or_not_bool <<= self.input_bit or not self.input_bool
            self.output_bool_or_not_bit <<= self.input_bool or not self.input_bit
            self.output_bool_or_not_bool <<= self.input_bool or not self.input_bool
            self.output_bit_or_not_bv <<= self.input_bit or not self.input_bitvector
            self.output_bv_or_not_bit <<= self.input_bitvector or not self.input_bit
            self.output_bool_or_not_bv <<= self.input_bool or not self.input_bitvector
            self.output_bv_or_not_bool <<= self.input_bitvector or not self.input_bool
            self.output_bv_or_not_bv <<= (
                self.input_bitvector or not self.input_bitvector
            )
            # not A or B
            self.output_not_bit_or_bit <<= not self.input_bit or self.input_bit
            self.output_not_bit_or_bool <<= not self.input_bit or self.input_bool
            self.output_not_bool_or_bit <<= not self.input_bool or self.input_bit
            self.output_not_bool_or_bool <<= not self.input_bool or self.input_bool
            self.output_not_bit_or_bv <<= not self.input_bit or self.input_bitvector
            self.output_not_bv_or_bit <<= not self.input_bitvector or self.input_bit
            self.output_not_bool_or_bv <<= not self.input_bool or self.input_bitvector
            self.output_not_bv_or_bool <<= not self.input_bitvector or self.input_bool
            self.output_not_bv_or_bv <<= (
                not self.input_bitvector or self.input_bitvector
            )


#
# test code
#


@cocotb_util.test()
async def testbench_boolean_02(dut: test_boolean_02):
    for inp_bit in gen(1).all():
        for inp_bool in gen(1).all():
            for inp_bv in gen(3).all():
                await cocotb_util.check_concurrent(
                    [
                        (dut.input_bit, inp_bit),
                        (dut.input_bool, inp_bool),
                        (dut.input_bitvector, inp_bv),
                        (dut.input_unsigned, inp_bv),
                        (dut.input_signed, inp_bv),
                    ],
                    [
                        (dut.output_test_bit, inp_bit),
                        (dut.output_test_bool, inp_bool),
                        (dut.output_test_bitvector, bool(inp_bv)),
                        (dut.output_test_unsigned, bool(inp_bv)),
                        (dut.output_test_signed, bool(inp_bv)),
                        (dut.output_test_int, bool(inp_bv)),
                        #
                        (dut.output_not_bit, not inp_bit),
                        (dut.output_not_bool, not inp_bool),
                        (dut.output_not_bitvector, not inp_bv),
                        (dut.output_not_unsigned, not inp_bv),
                        (dut.output_not_signed, not inp_bv),
                        (dut.output_not_int, not inp_bv),
                        # A and B
                        (dut.output_bit_and_bit, inp_bit and inp_bit),
                        (dut.output_bit_and_bool, inp_bit and inp_bool),
                        (dut.output_bool_and_bit, inp_bool and inp_bit),
                        (dut.output_bool_and_bool, inp_bool and inp_bool),
                        (dut.output_bit_and_bv, bool(inp_bit and inp_bv)),
                        (dut.output_bv_and_bool, bool(inp_bv and inp_bool)),
                        (dut.output_bool_and_bv, bool(inp_bool and inp_bv)),
                        (dut.output_bv_and_bit, bool(inp_bv and inp_bit)),
                        (dut.output_bv_and_bv, bool(inp_bv and inp_bv)),
                        # A and not B
                        (dut.output_bit_and_not_bit, inp_bit and not inp_bit),
                        (dut.output_bit_and_not_bool, inp_bit and not inp_bool),
                        (dut.output_bool_and_not_bit, inp_bool and not inp_bit),
                        (dut.output_bool_and_not_bool, inp_bool and not inp_bool),
                        (dut.output_bit_and_not_bv, bool(inp_bit and not inp_bv)),
                        (dut.output_bv_and_not_bool, bool(inp_bv and not inp_bool)),
                        (dut.output_bool_and_not_bv, bool(inp_bool and not inp_bv)),
                        (dut.output_bv_and_not_bit, bool(inp_bv and not inp_bit)),
                        (dut.output_bv_and_not_bv, bool(inp_bv and not inp_bv)),
                        # not A and B
                        (dut.output_not_bit_and_bit, not inp_bit and inp_bit),
                        (dut.output_not_bit_and_bool, not inp_bit and inp_bool),
                        (dut.output_not_bool_and_bit, not inp_bool and inp_bit),
                        (dut.output_not_bool_and_bool, not inp_bool and inp_bool),
                        (dut.output_not_bit_and_bv, bool(not inp_bit and inp_bv)),
                        (dut.output_not_bv_and_bool, bool(not inp_bv and inp_bool)),
                        (dut.output_not_bool_and_bv, bool(not inp_bool and inp_bv)),
                        (dut.output_not_bv_and_bit, bool(not inp_bv and inp_bit)),
                        (dut.output_not_bv_and_bv, bool(not inp_bv and inp_bv)),
                        #
                        # or
                        #
                        # A or B
                        (dut.output_bit_or_bit, inp_bit or inp_bit),
                        (dut.output_bit_or_bool, inp_bit or inp_bool),
                        (dut.output_bool_or_bit, inp_bool or inp_bit),
                        (dut.output_bool_or_bool, inp_bool or inp_bool),
                        (dut.output_bit_or_bv, bool(inp_bit or inp_bv)),
                        (dut.output_bv_or_bool, bool(inp_bv or inp_bool)),
                        (dut.output_bool_or_bv, bool(inp_bool or inp_bv)),
                        (dut.output_bv_or_bit, bool(inp_bv or inp_bit)),
                        (dut.output_bv_or_bv, bool(inp_bv or inp_bv)),
                        # A or not B
                        (dut.output_bit_or_not_bit, inp_bit or not inp_bit),
                        (dut.output_bit_or_not_bool, inp_bit or not inp_bool),
                        (dut.output_bool_or_not_bit, inp_bool or not inp_bit),
                        (dut.output_bool_or_not_bool, inp_bool or not inp_bool),
                        (dut.output_bit_or_not_bv, bool(inp_bit or not inp_bv)),
                        (dut.output_bv_or_not_bool, bool(inp_bv or not inp_bool)),
                        (dut.output_bool_or_not_bv, bool(inp_bool or not inp_bv)),
                        (dut.output_bv_or_not_bit, bool(inp_bv or not inp_bit)),
                        (dut.output_bv_or_not_bv, bool(inp_bv or not inp_bv)),
                        # not A or B
                        (dut.output_not_bit_or_bit, not inp_bit or inp_bit),
                        (dut.output_not_bit_or_bool, not inp_bit or inp_bool),
                        (dut.output_not_bool_or_bit, not inp_bool or inp_bit),
                        (dut.output_not_bool_or_bool, not inp_bool or inp_bool),
                        (dut.output_not_bit_or_bv, bool(not inp_bit or inp_bv)),
                        (dut.output_not_bv_or_bool, bool(not inp_bv or inp_bool)),
                        (dut.output_not_bool_or_bv, bool(not inp_bool or inp_bv)),
                        (dut.output_not_bv_or_bit, bool(not inp_bv or inp_bit)),
                        (dut.output_not_bv_or_bv, bool(not inp_bv or inp_bv)),
                        # complex expressions
                        (
                            dut.output_complex_a,
                            bool(inp_bit and inp_bool or not inp_bv),
                        ),
                        (dut.output_complex_b, not not not not not inp_bit),
                        (
                            dut.output_complex_c,
                            not not (
                                not (not not not inp_bit and inp_bool) or not not inp_bv
                            ),
                        ),
                        (dut.output_complex_d, bool(inp_bit and True or inp_bv)),
                        (dut.output_complex_e, bool(inp_bit or False or inp_bv)),
                    ],
                )


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_boolean_02, __file__, self.__module__)
