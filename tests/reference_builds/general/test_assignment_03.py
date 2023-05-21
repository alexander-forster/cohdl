from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Signal, Variable, Unsigned, Signed, Null
from cohdl import std

from cohdl_testutil import cocotb_util
from cohdl_testutil.cocotb_mock import MockBase


class test_assignment_03(cohdl.Entity):
    from_bitvector = Port.input(Bit)
    from_unsigned = Port.input(Bit)
    from_signed = Port.input(Bit)
    from_primitive = Port.input(Bit)
    from_str = Port.input(Bit)
    from_null_full = Port.input(Bit)

    inp_bitvector_short = Port.input(BitVector[4])
    inp_bitvector_long = Port.input(BitVector[8])
    inp_unsigned_short = Port.input(Unsigned[4])
    inp_unsigned_long = Port.input(Unsigned[8])
    inp_signed_short = Port.input(Signed[4])
    inp_signed_long = Port.input(Signed[8])

    out_bitvector_full_full = Port.output(BitVector[4])
    out_bitvector_full_slice = Port.output(BitVector[4])
    out_bitvector_slice_full = Port.output(BitVector[8])
    out_bitvector_slice_slice = Port.output(BitVector[8])

    out_unsigned_full_full = Port.output(Unsigned[4])
    out_unsigned_full_slice = Port.output(Unsigned[4])
    out_unsigned_slice_full = Port.output(Unsigned[8])
    out_unsigned_slice_slice = Port.output(Unsigned[8])

    out_signed_full_full = Port.output(Signed[4])
    out_signed_full_slice = Port.output(Signed[4])
    out_signed_slice_full = Port.output(Signed[8])
    out_signed_slice_slice = Port.output(Signed[8])

    def architecture(self):
        @std.sequential
        def logic_bitvector_target():
            if self.from_bitvector:
                self.out_bitvector_full_full <<= self.inp_bitvector_short
                self.out_bitvector_full_slice <<= self.inp_bitvector_long[3:0]
                self.out_bitvector_slice_full[3:0] <<= self.inp_bitvector_short
                self.out_bitvector_slice_full[7:4] <<= self.inp_bitvector_short
                self.out_bitvector_slice_slice[3:0] <<= self.inp_bitvector_long[3:0]
                self.out_bitvector_slice_slice[7:4] <<= self.inp_bitvector_long[7:4]
            elif self.from_unsigned:
                self.out_bitvector_full_full <<= self.inp_unsigned_short
                self.out_bitvector_full_slice <<= self.inp_unsigned_long[3:0]
                self.out_bitvector_slice_full[3:0] <<= self.inp_unsigned_short
                self.out_bitvector_slice_full[7:4] <<= self.inp_unsigned_short
                self.out_bitvector_slice_slice[3:0] <<= self.inp_unsigned_long[3:0]
                self.out_bitvector_slice_slice[7:4] <<= self.inp_unsigned_long[7:4]
            elif self.from_signed:
                self.out_bitvector_full_full <<= self.inp_signed_short
                self.out_bitvector_full_slice <<= self.inp_signed_long[3:0]
                self.out_bitvector_slice_full[3:0] <<= self.inp_signed_short
                self.out_bitvector_slice_full[7:4] <<= self.inp_signed_short
                self.out_bitvector_slice_slice[3:0] <<= self.inp_signed_long[3:0]
                self.out_bitvector_slice_slice[7:4] <<= self.inp_signed_long[7:4]
            elif self.from_primitive:
                self.out_bitvector_full_full <<= BitVector[4]("0000")
                self.out_bitvector_full_slice <<= BitVector[8]("00001111")[5:2]
                self.out_bitvector_slice_full[3:0] <<= BitVector[4]("0000")
                self.out_bitvector_slice_full[7:4] <<= BitVector[4]("1111")
                self.out_bitvector_slice_slice[3:0] <<= BitVector[8]("00001111")[5:2]
                self.out_bitvector_slice_slice[7:4] <<= BitVector[8]("11110000")[5:2]
            elif self.from_str:
                self.out_bitvector_full_full <<= "0000"
                self.out_bitvector_full_slice <<= "0011"
                self.out_bitvector_slice_full[3:0] <<= "0000"
                self.out_bitvector_slice_full[7:4] <<= "1111"
                self.out_bitvector_slice_slice[3:0] <<= "0011"
                self.out_bitvector_slice_slice[7:4] <<= "1100"
            elif self.from_null_full:
                self.out_bitvector_full_full <<= cohdl.Null
                self.out_bitvector_full_slice <<= cohdl.Full
                self.out_bitvector_slice_full[3:0] <<= cohdl.Null
                self.out_bitvector_slice_full[7:4] <<= cohdl.Full
                self.out_bitvector_slice_slice[3:0] <<= cohdl.Null
                self.out_bitvector_slice_slice[7:4] <<= cohdl.Full

        @std.sequential
        def logic_unsigned_target():
            if self.from_bitvector:
                self.out_unsigned_full_full <<= self.inp_bitvector_short
                self.out_unsigned_full_slice <<= self.inp_bitvector_long[3:0]
                self.out_unsigned_slice_full[3:0] <<= self.inp_bitvector_short
                self.out_unsigned_slice_full[7:4] <<= self.inp_bitvector_short
                self.out_unsigned_slice_slice[3:0] <<= self.inp_bitvector_long[3:0]
                self.out_unsigned_slice_slice[7:4] <<= self.inp_bitvector_long[7:4]
            elif self.from_unsigned:
                self.out_unsigned_full_full <<= self.inp_unsigned_short
                self.out_unsigned_full_slice <<= self.inp_unsigned_long[3:0]
                self.out_unsigned_slice_full[3:0] <<= self.inp_unsigned_short
                self.out_unsigned_slice_full[7:4] <<= self.inp_unsigned_short
                self.out_unsigned_slice_slice[3:0] <<= self.inp_unsigned_long[3:0]
                self.out_unsigned_slice_slice[7:4] <<= self.inp_unsigned_long[7:4]
            elif self.from_signed:
                # assignment of signed to unsigned requires cast
                self.out_unsigned_full_full <<= self.inp_signed_short.bitvector

                self.out_unsigned_full_slice <<= self.inp_signed_long[3:0]
                self.out_unsigned_slice_full[3:0] <<= self.inp_signed_short
                self.out_unsigned_slice_full[7:4] <<= self.inp_signed_short
                self.out_unsigned_slice_slice[3:0] <<= self.inp_signed_long[3:0]
                self.out_unsigned_slice_slice[7:4] <<= self.inp_signed_long[7:4]
            elif self.from_primitive:
                self.out_unsigned_full_full <<= Unsigned[4]("0000")
                self.out_unsigned_full_slice <<= Unsigned[8]("00001111")[5:2]
                self.out_unsigned_slice_full[3:0] <<= Unsigned[4]("0000")
                self.out_unsigned_slice_full[7:4] <<= BitVector[4]("1111")
                self.out_unsigned_slice_slice[3:0] <<= Unsigned[8]("00001111")[5:2]
                self.out_unsigned_slice_slice[7:4] <<= BitVector[8]("11110000")[5:2]
            elif self.from_str:
                self.out_unsigned_full_full <<= "0000"
                self.out_unsigned_full_slice <<= "0011"
                self.out_unsigned_slice_full[3:0] <<= "0000"
                self.out_unsigned_slice_full[7:4] <<= "1111"
                self.out_unsigned_slice_slice[3:0] <<= "0011"
                self.out_unsigned_slice_slice[7:4] <<= "1100"
            elif self.from_null_full:
                self.out_unsigned_full_full <<= cohdl.Null
                self.out_unsigned_full_slice <<= cohdl.Full
                self.out_unsigned_slice_full[3:0] <<= cohdl.Null
                self.out_unsigned_slice_full[7:4] <<= cohdl.Full
                self.out_unsigned_slice_slice[3:0] <<= cohdl.Null
                self.out_unsigned_slice_slice[7:4] <<= cohdl.Full

        @std.sequential
        def logic_signed_target():
            if self.from_bitvector:
                self.out_signed_full_full <<= self.inp_bitvector_short
                self.out_signed_full_slice <<= self.inp_bitvector_long[3:0]
                self.out_signed_slice_full[3:0] <<= self.inp_bitvector_short
                self.out_signed_slice_full[7:4] <<= self.inp_bitvector_short
                self.out_signed_slice_slice[3:0] <<= self.inp_bitvector_long[3:0]
                self.out_signed_slice_slice[7:4] <<= self.inp_bitvector_long[7:4]
            elif self.from_unsigned:
                self.out_signed_full_full <<= self.inp_unsigned_short.bitvector
                self.out_signed_full_slice <<= self.inp_unsigned_long[3:0]
                self.out_signed_slice_full[3:0] <<= self.inp_unsigned_short
                self.out_signed_slice_full[7:4] <<= self.inp_unsigned_short
                self.out_signed_slice_slice[3:0] <<= self.inp_unsigned_long[3:0]
                self.out_signed_slice_slice[7:4] <<= self.inp_unsigned_long[7:4]
            elif self.from_signed:
                self.out_signed_full_full <<= self.inp_signed_short
                self.out_signed_full_slice <<= self.inp_signed_long[3:0]
                self.out_signed_slice_full[3:0] <<= self.inp_signed_short
                self.out_signed_slice_full[7:4] <<= self.inp_signed_short
                self.out_signed_slice_slice[3:0] <<= self.inp_signed_long[3:0]
                self.out_signed_slice_slice[7:4] <<= self.inp_signed_long[7:4]
            elif self.from_primitive:
                self.out_signed_full_full <<= Signed[4]("0000")
                self.out_signed_full_slice <<= Signed[8]("00001111")[5:2]
                self.out_signed_slice_full[3:0] <<= Signed[4]("0000")
                self.out_signed_slice_full[7:4] <<= BitVector[4]("1111")
                self.out_signed_slice_slice[3:0] <<= Signed[8]("00001111")[5:2]
                self.out_signed_slice_slice[7:4] <<= BitVector[8]("11110000")[5:2]
            elif self.from_str:
                self.out_signed_full_full <<= "0000"
                self.out_signed_full_slice <<= "0011"
                self.out_signed_slice_full[3:0] <<= "0000"
                self.out_signed_slice_full[7:4] <<= "1111"
                self.out_signed_slice_slice[3:0] <<= "0011"
                self.out_signed_slice_slice[7:4] <<= "1100"
            elif self.from_null_full:
                self.out_signed_full_full <<= cohdl.Null
                self.out_signed_full_slice <<= cohdl.Full
                self.out_signed_slice_full[3:0] <<= cohdl.Null
                self.out_signed_slice_full[7:4] <<= cohdl.Full
                self.out_signed_slice_slice[3:0] <<= cohdl.Null
                self.out_signed_slice_slice[7:4] <<= cohdl.Full


#
# test code
#


@cocotb_util.test()
async def testbench_local_declaration_03(dut: test_assignment_03):
    short_gen = cocotb_util.ConstrainedGenerator(4)
    long_gen = cocotb_util.ConstrainedGenerator(8)

    for inp_choise in 1, 2, 3, 4, 5, 6:
        from_bitvector = inp_choise == 1
        from_unsigned = inp_choise == 2
        from_signed = inp_choise == 3
        from_primitive = inp_choise == 4
        from_str = inp_choise == 5
        from_null_full = inp_choise == 6

        for short in short_gen.random(16):
            short_short = short.as_int() << 4 | short.as_int()

            for long in long_gen.random(16):
                if from_bitvector or from_unsigned or from_signed:
                    checks = [
                        (dut.out_bitvector_full_full, short),
                        (dut.out_bitvector_full_slice, long.as_int() & 0xF),
                        (dut.out_bitvector_slice_full, short_short),
                        (dut.out_bitvector_slice_slice, long),
                        (dut.out_unsigned_full_full, short),
                        (dut.out_unsigned_full_slice, long.as_int() & 0xF),
                        (dut.out_unsigned_slice_full, short_short),
                        (dut.out_unsigned_slice_slice, long),
                        (dut.out_signed_full_full, short),
                        (dut.out_signed_full_slice, long.as_int() & 0xF),
                        (dut.out_signed_slice_full, short_short),
                        (dut.out_signed_slice_slice, long),
                    ]
                elif from_primitive or from_str:
                    checks = [
                        (dut.out_bitvector_full_full, 0),
                        (dut.out_bitvector_full_slice, 0b0011),
                        (dut.out_bitvector_slice_full, 0b11110000),
                        (dut.out_bitvector_slice_slice, 0b11000011),
                        (dut.out_unsigned_full_full, 0),
                        (dut.out_unsigned_full_slice, 0b0011),
                        (dut.out_unsigned_slice_full, 0b11110000),
                        (dut.out_unsigned_slice_slice, 0b11000011),
                        (dut.out_signed_full_full, 0),
                        (dut.out_signed_full_slice, 0b0011),
                        (dut.out_signed_slice_full, 0b11110000),
                        (dut.out_signed_slice_slice, 0b11000011),
                    ]
                elif from_null_full:
                    checks = [
                        (dut.out_bitvector_full_full, 0),
                        (dut.out_bitvector_full_slice, 0xF),
                        (dut.out_bitvector_slice_full, 0xF0),
                        (dut.out_bitvector_slice_slice, 0xF0),
                        (dut.out_unsigned_full_full, 0),
                        (dut.out_unsigned_full_slice, 0xF),
                        (dut.out_unsigned_slice_full, 0xF0),
                        (dut.out_unsigned_slice_slice, 0xF0),
                        (dut.out_signed_full_full, 0),
                        (dut.out_signed_full_slice, 0xF),
                        (dut.out_signed_slice_full, 0xF0),
                        (dut.out_signed_slice_slice, 0xF0),
                    ]
                else:
                    raise AssertionError("invalid choise")

                await cocotb_util.check_concurrent(
                    [
                        (dut.from_bitvector, from_bitvector),
                        (dut.from_unsigned, from_unsigned),
                        (dut.from_signed, from_signed),
                        (dut.from_primitive, from_primitive),
                        (dut.from_str, from_str),
                        (dut.from_null_full, from_null_full),
                        (dut.inp_bitvector_short, short),
                        (dut.inp_bitvector_long, long),
                        (dut.inp_unsigned_short, short),
                        (dut.inp_unsigned_long, long),
                        (dut.inp_signed_short, short),
                        (dut.inp_signed_long, long),
                    ],
                    checks,
                )


class Unittest(unittest.TestCase):
    def test_assignment_03(self):
        cocotb_util.run_cocotb_tests(
            test_assignment_03, __file__, self.__module__, no_build=False
        )


print(std.VhdlCompiler.to_string(test_assignment_03))
