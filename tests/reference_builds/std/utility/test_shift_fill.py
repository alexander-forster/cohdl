from __future__ import annotations

import unittest

import cohdl
from cohdl import std, BitVector, Port

from cohdl_testutil import cocotb_util


class test_shift_fill(cohdl.Entity):
    inp_base_1 = Port.input(BitVector[1])
    inp_base_2 = Port.input(BitVector[2])
    inp_base_5 = Port.input(BitVector[5])

    inp_fill = Port.input(BitVector[5])

    lout_1_bit = Port.output(BitVector[1])
    lout_1_1 = Port.output(BitVector[1])

    lout_2_bit = Port.output(BitVector[2])
    lout_2_1 = Port.output(BitVector[2])
    lout_2_2 = Port.output(BitVector[2])

    lout_5_bit = Port.output(BitVector[5])
    lout_5_1 = Port.output(BitVector[5])
    lout_5_2 = Port.output(BitVector[5])
    lout_5_5 = Port.output(BitVector[5])

    #
    #
    #

    rout_1_bit = Port.output(BitVector[1])
    rout_1_1 = Port.output(BitVector[1])

    rout_2_bit = Port.output(BitVector[2])
    rout_2_1 = Port.output(BitVector[2])
    rout_2_2 = Port.output(BitVector[2])

    rout_5_bit = Port.output(BitVector[5])
    rout_5_1 = Port.output(BitVector[5])
    rout_5_2 = Port.output(BitVector[5])
    rout_5_5 = Port.output(BitVector[5])

    def architecture(self):
        @std.concurrent
        def proc_out():
            self.lout_1_bit <<= std.lshift_fill(self.inp_base_1, self.inp_fill[0])
            self.lout_1_1 <<= std.lshift_fill(self.inp_base_1, self.inp_fill[0:0])

            self.lout_2_bit <<= std.lshift_fill(self.inp_base_2, self.inp_fill[0])
            self.lout_2_1 <<= std.lshift_fill(self.inp_base_2, self.inp_fill[0:0])
            self.lout_2_2 <<= std.lshift_fill(self.inp_base_2, self.inp_fill[1:0])

            self.lout_5_bit <<= std.lshift_fill(self.inp_base_5, self.inp_fill[0])
            self.lout_5_1 <<= std.lshift_fill(self.inp_base_5, self.inp_fill[0:0])
            self.lout_5_2 <<= std.lshift_fill(self.inp_base_5, self.inp_fill[1:0])
            self.lout_5_5 <<= std.lshift_fill(self.inp_base_5, self.inp_fill[4:0])

            #
            #
            #

            self.rout_1_bit <<= std.rshift_fill(self.inp_base_1, self.inp_fill[0])
            self.rout_1_1 <<= std.rshift_fill(self.inp_base_1, self.inp_fill[0:0])

            self.rout_2_bit <<= std.rshift_fill(self.inp_base_2, self.inp_fill[0])
            self.rout_2_1 <<= std.rshift_fill(self.inp_base_2, self.inp_fill[0:0])
            self.rout_2_2 <<= std.rshift_fill(self.inp_base_2, self.inp_fill[1:0])

            self.rout_5_bit <<= std.rshift_fill(self.inp_base_5, self.inp_fill[0])
            self.rout_5_1 <<= std.rshift_fill(self.inp_base_5, self.inp_fill[0:0])
            self.rout_5_2 <<= std.rshift_fill(self.inp_base_5, self.inp_fill[1:0])
            self.rout_5_5 <<= std.rshift_fill(self.inp_base_5, self.inp_fill[4:0])


#
# test code
#


def mock_lshift_fill(
    base: cocotb_util.ConstraindValue, fill: cocotb_util.ConstraindValue
):
    fill_width = fill.width
    base_width = base.width

    return ((base.as_int() << fill_width) & ((1 << base_width) - 1)) | fill.as_int()


def mock_rshift_fill(
    base: cocotb_util.ConstraindValue, fill: cocotb_util.ConstraindValue
):
    fill_width = fill.width
    base_width = base.width

    return ((base.as_int() >> fill_width) & ((1 << base_width) - 1)) | (
        fill.as_int() << (base_width - fill_width)
    )


@cocotb_util.test()
async def testbench_shift_fill(dut: test_shift_fill):
    gen_base1 = cocotb_util.ConstrainedGenerator(1)
    gen_base2 = cocotb_util.ConstrainedGenerator(2)
    gen_base5 = cocotb_util.ConstrainedGenerator(5)
    gen_fill = cocotb_util.ConstrainedGenerator(5)

    for _ in range(64):
        base1 = gen_base1.random()
        base2 = gen_base2.random()
        base5 = gen_base5.random()
        fill = gen_fill.random()

        dut.inp_base_1.value = base1.as_int()
        dut.inp_base_2.value = base2.as_int()
        dut.inp_base_5.value = base5.as_int()
        dut.inp_fill.value = fill.as_int()
        await cocotb_util.step()

        assert dut.lout_1_bit.value == mock_lshift_fill(base1, fill.get_slice(0, 0))
        assert dut.lout_1_1.value == mock_lshift_fill(base1, fill.get_slice(0, 0))

        assert dut.lout_2_bit.value == mock_lshift_fill(base2, fill.get_slice(0, 0))
        assert dut.lout_2_1.value == mock_lshift_fill(base2, fill.get_slice(0, 0))
        assert dut.lout_2_2.value == mock_lshift_fill(base2, fill.get_slice(0, 1))

        assert dut.lout_5_bit.value == mock_lshift_fill(base5, fill.get_slice(0, 0))
        assert dut.lout_5_1.value == mock_lshift_fill(base5, fill.get_slice(0, 0))
        assert dut.lout_5_2.value == mock_lshift_fill(base5, fill.get_slice(0, 1))
        assert dut.lout_5_5.value == mock_lshift_fill(base5, fill.get_slice(0, 4))

        #
        #

        assert dut.rout_1_bit.value == mock_rshift_fill(base1, fill.get_slice(0, 0))
        assert dut.rout_1_1.value == mock_rshift_fill(base1, fill.get_slice(0, 0))

        assert dut.rout_2_bit.value == mock_rshift_fill(base2, fill.get_slice(0, 0))
        assert dut.rout_2_1.value == mock_rshift_fill(base2, fill.get_slice(0, 0))
        assert dut.rout_2_2.value == mock_rshift_fill(base2, fill.get_slice(0, 1))

        assert dut.rout_5_bit.value == mock_rshift_fill(base5, fill.get_slice(0, 0))
        assert dut.rout_5_1.value == mock_rshift_fill(base5, fill.get_slice(0, 0))
        assert dut.rout_5_2.value == mock_rshift_fill(base5, fill.get_slice(0, 1))
        assert dut.rout_5_5.value == mock_rshift_fill(base5, fill.get_slice(0, 4))


class Unittest(unittest.TestCase):
    def test_shift_fill(self):
        cocotb_util.run_cocotb_tests(test_shift_fill, __file__, self.__module__)
