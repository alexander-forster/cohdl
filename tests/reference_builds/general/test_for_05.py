import unittest

import cohdl
from cohdl import Bit, Port, BitVector, Unsigned
from cohdl import std

from cohdl_testutil import cocotb_util


class test_for_05(cohdl.Entity):
    clk = Port.input(Bit)
    reset = Port.input(Bit)

    input = Port.input(BitVector[3])
    sel = Port.input(Unsigned[2])

    result = Port.output(Bit, default=False)

    def architecture(self):
        @std.sequential(std.Clock(self.clk), std.Reset(self.reset))
        async def proc():
            await self.input

            for nr, bit in enumerate(self.input):
                if nr == self.sel:
                    await bit
                    break
            else:
                await self.input

            self.result ^= True


#
# test code
#

@cocotb_util.test()
async def testbench_for_05(dut: test_for_05):
    gen_select = cocotb_util.ConstrainedGenerator(2)
    gen_input = cocotb_util.ConstrainedGenerator(3)

    seq = cocotb_util.SequentialTest(dut.clk)

    dut.reset.value = True
    await seq.tick()
    dut.reset.value = False

    for _ in range(64):
        select = gen_select.random()
        dut.sel.value = select.as_int()
        await seq.tick()

        while True:
            input = gen_input.random()
            dut.input.value = input.as_int()

            expected = bool(input.get_bit(select.as_int()) if select.as_int() != 3 else input)

            await seq.tick()

            assert dut.result.value == expected

            if expected:
                break

class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_for_05, __file__, self.__module__)
