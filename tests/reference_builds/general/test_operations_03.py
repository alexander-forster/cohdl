import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Unsigned, Signed, Integer, Signal
from cohdl import std
from cohdl_testutil import cocotb_util


class simple_shift(cohdl.Entity):
    inp_shift = Port.input(Unsigned[4])

    inp_signed = Port.input(Signed[8])
    inp_unsigned = Port.input(Unsigned[8])

    out_s_left_0 = Port.output(Signed[8])
    out_s_left_1 = Port.output(Signed[8])
    out_s_left_4 = Port.output(Signed[8])
    out_u_left_0 = Port.output(Unsigned[8])
    out_u_left_1 = Port.output(Unsigned[8])
    out_u_left_4 = Port.output(Unsigned[8])

    out_s_right_0 = Port.output(Signed[8])
    out_s_right_1 = Port.output(Signed[8])
    out_s_right_4 = Port.output(Signed[8])
    out_u_right_0 = Port.output(Unsigned[8])
    out_u_right_1 = Port.output(Unsigned[8])
    out_u_right_4 = Port.output(Unsigned[8])

    out_s_left = Port.output(Signed[8])
    out_u_left = Port.output(Unsigned[8])

    out_s_right = Port.output(Signed[8])
    out_u_right = Port.output(Unsigned[8])

    def architecture(self):
        int_shift = Integer(1)
        int_sig_shift = Signal[Integer](4)

        @std.concurrent
        def logic():
            self.out_s_left_0 <<= self.inp_signed << 0
            self.out_s_left_1 <<= self.inp_signed << int_shift
            self.out_s_left_4 <<= self.inp_signed << int_sig_shift

            self.out_u_left_0 <<= self.inp_unsigned << 0
            self.out_u_left_1 <<= self.inp_unsigned << int_shift
            self.out_u_left_4 <<= self.inp_unsigned << int_sig_shift

            self.out_s_right_0 <<= self.inp_signed >> 0
            self.out_s_right_1 <<= self.inp_signed >> int_shift
            self.out_s_right_4 <<= self.inp_signed >> int_sig_shift
            self.out_u_right_0 <<= self.inp_unsigned >> 0
            self.out_u_right_1 <<= self.inp_unsigned >> int_shift
            self.out_u_right_4 <<= self.inp_unsigned >> int_sig_shift

            self.out_s_left <<= self.inp_signed << self.inp_shift
            self.out_u_left <<= self.inp_unsigned << self.inp_shift

            self.out_s_right <<= self.inp_signed >> self.inp_shift
            self.out_u_right <<= self.inp_unsigned >> self.inp_shift


@cocotb_util.test()
async def testbench_simple_shift(dut: simple_shift):
    gen_shift = cocotb_util.ConstrainedGenerator(4)
    vector_gen = cocotb_util.ConstrainedGenerator(8)

    for _ in range(100):
        inp_shift = gen_shift.random()
        inp_signed = vector_gen.random()
        inp_unsigned = vector_gen.random()

        cocotb_util.assign(dut.inp_shift, inp_shift)
        cocotb_util.assign(dut.inp_unsigned, inp_unsigned)
        cocotb_util.assign(dut.inp_signed, inp_signed)

        await cocotb_util.step()

        assert dut.out_s_left_0 == inp_signed
        assert dut.out_s_left_1 == (inp_signed << 1)
        assert dut.out_s_left_4 == (inp_signed << 4)

        assert dut.out_u_left_0 == inp_unsigned
        assert dut.out_u_left_1 == (inp_unsigned << 1)
        assert dut.out_u_left_4 == (inp_unsigned << 4)

        assert dut.out_s_right_0 == inp_signed
        assert dut.out_s_right_1 == (inp_signed.signed_rshift(1))
        assert dut.out_s_right_4 == (inp_signed.signed_rshift(4))

        assert dut.out_u_right_0 == inp_unsigned
        assert dut.out_u_right_1 == (inp_unsigned >> 1)
        assert dut.out_u_right_4 == (inp_unsigned >> 4)

        assert dut.out_s_left == (inp_signed << inp_shift.as_int())
        assert dut.out_u_left == (inp_unsigned << inp_shift.as_int())

        assert dut.out_s_right == (inp_signed.signed_rshift(inp_shift.as_int()))
        assert dut.out_u_right == (inp_unsigned >> inp_shift.as_int())


class Unittest(unittest.TestCase):
    def test_concurrent(self):
        cocotb_util.run_cocotb_tests(simple_shift, __file__, self.__module__)
