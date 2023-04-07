import unittest

import cohdl
from cohdl import BitVector, Port
from cohdl import std


from cohdl_testutil import cocotb_util


class test_for_02(cohdl.Entity):
    port_in = Port.input(BitVector[8])
    port_out = Port.output(BitVector[8])

    def architecture(self):
        @std.concurrent
        def logic():
            for i in range(8):
                self.port_out[i] <<= self.port_in[i]


@cocotb_util.test()
async def testbench_for_02(dut: test_for_02):
    for i in range(256):
        dut.port_in <= i
        await cocotb_util.step()
        assert dut.port_out.value == i


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_for_02, __file__, self.__module__)
