import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Signed, Unsigned, select_with, Null
from cohdl import std
import random

from cohdl_testutil import cocotb_util


class test_resize_01(cohdl.Entity):
    input_v = Port.input(BitVector[8])
    input_s = Port.input(Signed[8])
    input_u = Port.input(Unsigned[8])

    v_out_s_16 = Port.output(Signed[16])
    v_out_u_16 = Port.output(Unsigned[16])
    v_out_s_16_0 = Port.output(Signed[16])
    v_out_u_16_0 = Port.output(Unsigned[16])
    v_out_s_16_1 = Port.output(Signed[16])
    v_out_u_16_1 = Port.output(Unsigned[16])
    v_out_s_16_4 = Port.output(Signed[16])
    v_out_u_16_4 = Port.output(Unsigned[16])
    v_out_s_x_0 = Port.output(Signed[8])
    v_out_u_x_0 = Port.output(Unsigned[8])
    v_out_s_x_1 = Port.output(Signed[9])
    v_out_u_x_1 = Port.output(Unsigned[9])
    v_out_s_x_4 = Port.output(Signed[12])
    v_out_u_x_4 = Port.output(Unsigned[12])

    s_out_s_16 = Port.output(Signed[16])
    s_out_u_16 = Port.output(Unsigned[16])
    s_out_s_16_0 = Port.output(Signed[16])
    s_out_u_16_0 = Port.output(Unsigned[16])
    s_out_s_16_1 = Port.output(Signed[16])
    s_out_u_16_1 = Port.output(Unsigned[16])
    s_out_s_16_4 = Port.output(Signed[16])
    s_out_u_16_4 = Port.output(Unsigned[16])
    s_out_s_x_0 = Port.output(Signed[8])
    s_out_u_x_0 = Port.output(Unsigned[8])
    s_out_s_x_1 = Port.output(Signed[9])
    s_out_u_x_1 = Port.output(Unsigned[9])
    s_out_s_x_4 = Port.output(Signed[12])
    s_out_u_x_4 = Port.output(Unsigned[12])

    u_out_s_16 = Port.output(Signed[16])
    u_out_u_16 = Port.output(Unsigned[16])
    u_out_s_16_0 = Port.output(Signed[16])
    u_out_u_16_0 = Port.output(Unsigned[16])
    u_out_s_16_1 = Port.output(Signed[16])
    u_out_u_16_1 = Port.output(Unsigned[16])
    u_out_s_16_4 = Port.output(Signed[16])
    u_out_u_16_4 = Port.output(Unsigned[16])
    u_out_s_x_0 = Port.output(Signed[8])
    u_out_u_x_0 = Port.output(Unsigned[8])
    u_out_s_x_1 = Port.output(Signed[9])
    u_out_u_x_1 = Port.output(Unsigned[9])
    u_out_s_x_4 = Port.output(Signed[12])
    u_out_u_x_4 = Port.output(Unsigned[12])

    def architecture(self):
        @std.concurrent
        def logic():
            # input is vector

            self.v_out_s_16 <<= self.input_v.signed.resize(16)
            self.v_out_u_16 <<= self.input_v.unsigned.resize(16)

            self.v_out_s_16_0 <<= self.input_v.signed.resize(16, zeros=0)
            self.v_out_u_16_0 <<= self.input_v.unsigned.resize(16, zeros=0)
            self.v_out_s_16_1 <<= self.input_v.signed.resize(16, zeros=1)
            self.v_out_u_16_1 <<= self.input_v.unsigned.resize(16, zeros=1)
            self.v_out_s_16_4 <<= self.input_v.signed.resize(16, zeros=4)
            self.v_out_u_16_4 <<= self.input_v.unsigned.resize(16, zeros=4)

            self.v_out_s_x_0 <<= self.input_v.signed.resize(zeros=0)
            self.v_out_u_x_0 <<= self.input_v.unsigned.resize(zeros=0)
            self.v_out_s_x_1 <<= self.input_v.signed.resize(zeros=1)
            self.v_out_u_x_1 <<= self.input_v.unsigned.resize(zeros=1)
            self.v_out_s_x_4 <<= self.input_v.signed.resize(zeros=4)
            self.v_out_u_x_4 <<= self.input_v.unsigned.resize(zeros=4)

            # input is signed

            self.s_out_s_16 <<= self.input_s.resize(16)
            self.s_out_u_16 <<= self.input_s.unsigned.resize(16)
            self.s_out_s_16_0 <<= self.input_s.resize(16, zeros=0)
            self.s_out_u_16_0 <<= self.input_s.unsigned.resize(16, zeros=0)
            self.s_out_s_16_1 <<= self.input_s.resize(16, zeros=1)
            self.s_out_u_16_1 <<= self.input_s.unsigned.resize(16, zeros=1)
            self.s_out_s_16_4 <<= self.input_s.resize(16, zeros=4)
            self.s_out_u_16_4 <<= self.input_s.unsigned.resize(16, zeros=4)
            self.s_out_s_x_0 <<= self.input_s.resize(zeros=0)
            self.s_out_u_x_0 <<= self.input_s.unsigned.resize(zeros=0)
            self.s_out_s_x_1 <<= self.input_s.resize(zeros=1)
            self.s_out_u_x_1 <<= self.input_s.unsigned.resize(zeros=1)
            self.s_out_s_x_4 <<= self.input_s.resize(zeros=4)
            self.s_out_u_x_4 <<= self.input_s.unsigned.resize(zeros=4)

            # input is unsigned

            self.u_out_s_16 <<= self.input_u.signed.resize(16)
            self.u_out_u_16 <<= self.input_u.resize(16)
            self.u_out_s_16_0 <<= self.input_u.signed.resize(16, zeros=0)
            self.u_out_u_16_0 <<= self.input_u.resize(16, zeros=0)
            self.u_out_s_16_1 <<= self.input_u.signed.resize(16, zeros=1)
            self.u_out_u_16_1 <<= self.input_u.resize(16, zeros=1)
            self.u_out_s_16_4 <<= self.input_u.signed.resize(16, zeros=4)
            self.u_out_u_16_4 <<= self.input_u.resize(16, zeros=4)
            self.u_out_s_x_0 <<= self.input_u.signed.resize(zeros=0)
            self.u_out_u_x_0 <<= self.input_u.resize(zeros=0)
            self.u_out_s_x_1 <<= self.input_u.signed.resize(zeros=1)
            self.u_out_u_x_1 <<= self.input_u.resize(zeros=1)
            self.u_out_s_x_4 <<= self.input_u.signed.resize(zeros=4)
            self.u_out_u_x_4 <<= self.input_u.resize(zeros=4)


@cocotb_util.test()
async def testbench_simple(dut: test_resize_01):
    value_gen = cocotb_util.ConstrainedGenerator(8)

    for _ in range(100):
        v = value_gen.random()
        s = value_gen.random()
        u = value_gen.random()

        cocotb_util.assign(dut.input_v, v)
        cocotb_util.assign(dut.input_s, s)
        cocotb_util.assign(dut.input_u, u)

        await cocotb_util.step()
        await cocotb_util.step()

        assert dut.v_out_s_16.value.signed_integer == v.signed()
        assert dut.v_out_u_16.value == v
        assert dut.v_out_s_16_0.value.signed_integer == v.signed()
        assert dut.v_out_u_16_0.value == v
        assert dut.v_out_s_16_1.value.signed_integer == v.signed() * 2
        assert dut.v_out_u_16_1.value == v * 2
        assert dut.v_out_s_16_4.value.signed_integer == v.signed() * 16
        assert dut.v_out_u_16_4.value == v * 16
        assert dut.v_out_s_x_0.value.signed_integer == v.signed()
        assert dut.v_out_u_x_0.value == v
        assert dut.v_out_s_x_1.value.signed_integer == v.signed() * 2
        assert dut.v_out_u_x_1.value == v * 2
        assert dut.v_out_s_x_4.value.signed_integer == v.signed() * 16
        assert dut.v_out_u_x_4.value == v * 16

        assert dut.s_out_s_16.value.signed_integer == s.signed()
        assert dut.s_out_u_16.value == s
        assert dut.s_out_s_16_0.value.signed_integer == s.signed()
        assert dut.s_out_u_16_0.value == s
        assert dut.s_out_s_16_1.value.signed_integer == s.signed() * 2
        assert dut.s_out_u_16_1.value == s * 2
        assert dut.s_out_s_16_4.value.signed_integer == s.signed() * 16
        assert dut.s_out_u_16_4.value == s * 16
        assert dut.s_out_s_x_0.value.signed_integer == s.signed()
        assert dut.s_out_u_x_0.value == s
        assert dut.s_out_s_x_1.value.signed_integer == s.signed() * 2
        assert dut.s_out_u_x_1.value == s * 2
        assert dut.s_out_s_x_4.value.signed_integer == s.signed() * 16
        assert dut.s_out_u_x_4.value == s * 16

        assert dut.u_out_s_16.value.signed_integer == u.signed()
        assert dut.u_out_u_16.value == u
        assert dut.u_out_s_16_0.value.signed_integer == u.signed()
        assert dut.u_out_u_16_0.value == u
        assert dut.u_out_s_16_1.value.signed_integer == u.signed() * 2
        assert dut.u_out_u_16_1.value == u * 2
        assert dut.u_out_s_16_4.value.signed_integer == u.signed() * 16
        assert dut.u_out_u_16_4.value == u * 16
        assert dut.u_out_s_x_0.value.signed_integer == u.signed()
        assert dut.u_out_u_x_0.value == u
        assert dut.u_out_s_x_1.value.signed_integer == u.signed() * 2
        assert dut.u_out_u_x_1.value == u * 2
        assert dut.u_out_s_x_4.value.signed_integer == u.signed() * 16
        assert dut.u_out_u_x_4.value == u * 16


class Unittest(unittest.TestCase):
    def test_concurrent(self):
        cocotb_util.run_cocotb_tests(test_resize_01, __file__, self.__module__)
