from __future__ import annotations


import unittest

import cohdl
from cohdl import Bit, BitVector, Port
from cohdl import std

from cohdl_testutil import cocotb_util
from cohdl_testutil.cocotb_mock import MockBase


class ValHolder:
    def __init__(self, val):
        self.val = val


class test_value_branch_01(cohdl.Entity):

    enable = Port.input(Bit)

    inp1 = Port.input(BitVector[4])
    inp2 = Port.input(BitVector[4])

    output1 = Port.output(BitVector[4])
    output2 = Port.output(BitVector[4])
    output3 = Port.output(Bit)

    def architecture(self):
        @std.concurrent
        def proc():

            v = ValHolder(self.inp1) if self.enable else ValHolder(self.inp2)

            assert hasattr(v, "val")
            assert not hasattr(v, "asdf")

            self.output1 <<= v.val
            self.output2 <<= getattr(v, "val")
            self.output3 <<= getattr(
                ValHolder(v.val[2]) if self.inp1[0] else ValHolder(self.inp2[3]), "val"
            )


#
# test code
#


@cocotb_util.test()
async def testbench_value_branch_01(dut: test_value_branch_01):

    for a in range(16):
        for b in range(16):
            for en in (True, False):
                out12 = a if en else b

                cocotb_util.check_concurrent(
                    [(dut.enable, en), (dut.inp1, a), (dut.inp2, b)],
                    [
                        (dut.output1, out12),
                        (dut.output2, out12),
                        (
                            dut.output3,
                            ((out12 >> 2) & 1) if (a & 1) else ((b >> 3) & 1),
                        ),
                    ],
                )


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_value_branch_01, __file__, self.__module__)
