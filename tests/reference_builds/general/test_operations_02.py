import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Unsigned, Signed
from cohdl import std

from cohdl_testutil import cocotb_util


class simple_concat(cohdl.Entity):
    inp_bit = Port.input(Bit)
    inp_vector = Port.input(BitVector[8])
    inp_signed = Port.input(Signed[8])
    inp_unsigned = Port.input(Unsigned[8])

    out_concat_b_b = Port.output(BitVector[2])
    out_concat_b_v = Port.output(BitVector[9])
    out_concat_b_u = Port.output(BitVector[9])
    out_concat_b_s = Port.output(BitVector[9])

    out_concat_v_b = Port.output(BitVector[9])
    out_concat_v_v = Port.output(BitVector[16])
    out_concat_v_u = Port.output(BitVector[16])
    out_concat_v_s = Port.output(BitVector[16])

    out_concat_u_b = Port.output(BitVector[9])
    out_concat_u_u = Port.output(BitVector[16])
    out_concat_u_v = Port.output(BitVector[16])
    out_concat_u_s = Port.output(BitVector[16])

    out_concat_s_b = Port.output(BitVector[9])
    out_concat_s_s = Port.output(BitVector[16])
    out_concat_s_u = Port.output(BitVector[16])
    out_concat_s_v = Port.output(BitVector[16])

    def architecture(self):
        @std.concurrent
        def logic():
            self.out_concat_b_b <<= self.inp_bit @ self.inp_bit
            self.out_concat_b_v <<= self.inp_bit @ self.inp_vector
            self.out_concat_b_u <<= self.inp_bit @ self.inp_unsigned
            self.out_concat_b_s <<= self.inp_bit @ self.inp_signed

            self.out_concat_v_b <<= self.inp_vector @ self.inp_bit
            self.out_concat_v_v <<= self.inp_vector @ self.inp_vector
            self.out_concat_v_u <<= self.inp_vector @ self.inp_unsigned
            self.out_concat_v_s <<= self.inp_vector @ self.inp_signed

            self.out_concat_u_b <<= self.inp_unsigned @ self.inp_bit
            self.out_concat_u_u <<= self.inp_unsigned @ self.inp_unsigned
            self.out_concat_u_v <<= self.inp_unsigned @ self.inp_vector
            self.out_concat_u_s <<= self.inp_unsigned @ self.inp_signed

            self.out_concat_s_b <<= self.inp_signed @ self.inp_bit
            self.out_concat_s_s <<= self.inp_signed @ self.inp_signed
            self.out_concat_s_u <<= self.inp_signed @ self.inp_unsigned
            self.out_concat_s_v <<= self.inp_signed @ self.inp_vector


@cocotb_util.test()
async def testbench_simple_concat(dut: simple_concat):
    bit_gen = cocotb_util.ConstrainedGenerator(1)
    vector_gen = cocotb_util.ConstrainedGenerator(8)

    for _ in range(100):
        inp_bit = bit_gen.random()
        inp_vector = vector_gen.random()
        inp_unsigned = vector_gen.random()
        inp_signed = vector_gen.random()

        cocotb_util.assign(dut.inp_bit, inp_bit)
        cocotb_util.assign(dut.inp_vector, inp_vector)
        cocotb_util.assign(dut.inp_unsigned, inp_unsigned)
        cocotb_util.assign(dut.inp_signed, inp_signed)

        await cocotb_util.step()

        assert dut.out_concat_b_b == inp_bit @ inp_bit
        assert dut.out_concat_b_v == inp_bit @ inp_vector
        assert dut.out_concat_b_u == inp_bit @ inp_unsigned
        assert dut.out_concat_b_s == inp_bit @ inp_signed

        assert dut.out_concat_v_b == inp_vector @ inp_bit
        assert dut.out_concat_v_v == inp_vector @ inp_vector
        assert dut.out_concat_v_u == inp_vector @ inp_unsigned
        assert dut.out_concat_v_s == inp_vector @ inp_signed

        assert dut.out_concat_u_b == inp_unsigned @ inp_bit
        assert dut.out_concat_u_u == inp_unsigned @ inp_unsigned
        assert dut.out_concat_u_v == inp_unsigned @ inp_vector
        assert dut.out_concat_u_s == inp_unsigned @ inp_signed

        assert dut.out_concat_s_b == inp_signed @ inp_bit
        assert dut.out_concat_s_s == inp_signed @ inp_signed
        assert dut.out_concat_s_u == inp_signed @ inp_unsigned
        assert dut.out_concat_s_v == inp_signed @ inp_vector


class Unittest(unittest.TestCase):
    def test_concurrent(self):
        cocotb_util.run_cocotb_tests(simple_concat, __file__, self.__module__)
