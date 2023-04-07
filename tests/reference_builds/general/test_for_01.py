import unittest

import cohdl
from cohdl import BitVector, Port
from cohdl import std


from cohdl_testutil import cocotb_util


class test_for(cohdl.Entity):
    port_in = Port.input(BitVector[8])
    port_out = Port.output(BitVector[8])

    def architecture(self):
        @std.concurrent
        def logic():
            for inp, out in zip(self.port_in, self.port_out):
                out <<= inp


@cocotb_util.test()
async def testbench_simple(dut: test_for):
    for i in range(256):
        dut.port_in <= i
        await cocotb_util.step()
        assert dut.port_out.value == i


class Unittest(unittest.TestCase):
    def test_concurrent(self):
        cocotb_util.run_cocotb_tests(test_for, __file__, self.__module__)
