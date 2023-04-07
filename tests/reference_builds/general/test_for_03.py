import unittest


import unittest

import cohdl
from cohdl import Bit, Port, BitVector
from cohdl import std

from cohdl_testutil import cocotb_util


class test_for_03(cohdl.Entity):
    value = Port.input(BitVector[16])
    mask = Port.input(BitVector[16])
    result = Port.output(Bit)

    def architecture(self):
        @std.sequential
        async def proc():
            for val, mask in zip(self.value, self.mask):
                if mask:
                    self.result <<= val
                    break
            else:
                self.result <<= False


#
# test code
#


@cocotb_util.test()
async def testbench_for_02(dut: test_for_03):
    gen = cocotb_util.ConstrainedGenerator(16)

    for value in gen.random(64, required=[0, 1]):
        for mask in gen.random(64, required=[0, 1]):
            int_mask = mask.as_int()
            int_value = value.as_int()
            dut.mask.value = int_mask
            dut.value.value = int_value

            await cocotb_util.step()

            for bitNr in range(16):
                if (1 << bitNr) & int_mask:
                    expected = bool(int_value & (1 << bitNr))
                    break
            else:
                expected = 0

            assert dut.result == expected


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_for_03, __file__, self.__module__)
