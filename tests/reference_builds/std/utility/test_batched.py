from __future__ import annotations

import unittest

import cohdl
from cohdl import std, BitVector, Unsigned, Port, Signal, Null, Full

from cohdl_testutil import cocotb_util


class test_batched(cohdl.Entity):
    input = Port.input(BitVector[6])

    output_1 = Port.output(BitVector[6])
    output_2 = Port.output(BitVector[6])
    output_6 = Port.output(BitVector[6])

    selector_1 = Port.input(BitVector[6])
    selector_2 = Port.input(BitVector[3])
    selector_6 = Port.input(BitVector[1])

    selected_1 = Port.output(BitVector[1])
    selected_2 = Port.output(BitVector[2])
    selected_6 = Port.output(BitVector[6])

    def architecture(self):
        @std.concurrent
        def logic():
            for inp, out in zip(
                std.batched(self.input, 1), std.batched(self.output_1, 1)
            ):
                out <<= inp

            for inp, out in zip(
                std.batched(self.input, 2), std.batched(self.output_2, 2)
            ):
                out <<= inp

            for inp, out in zip(
                std.batched(self.input, 6), std.batched(self.output_6, 6)
            ):
                out <<= inp

            self.selected_1 <<= std.select_batch(self.input, self.selector_1, 1)
            self.selected_2 <<= std.select_batch(self.input, self.selector_2, 2)
            self.selected_6 <<= std.select_batch(self.input, self.selector_6, 6)


#
# test code
#


@cocotb_util.test()
async def testbench_batched(dut: test_batched):
    selector = 0

    for input in range(2**6):
        dut.input.value = input

        dut.selector_1.value = 1 << (selector % 6)
        dut.selector_2.value = 1 << (selector % 3)
        dut.selector_6.value = 1

        await cocotb_util.step()

        assert dut.output_1.value == input
        assert dut.output_2.value == input
        assert dut.output_6.value == input

        assert dut.selected_1.value == (input >> (selector % 6)) & 1
        assert dut.selected_2.value == (input >> (selector % 3 * 2)) & 3
        assert dut.selected_6.value == input

        dut.selector_1.value = 0
        dut.selector_2.value = 0
        dut.selector_6.value = 0

        await cocotb_util.step()

        assert dut.selected_1.value == 0
        assert dut.selected_2.value == 0
        assert dut.selected_6.value == 0


class Unittest(unittest.TestCase):
    def test_hdl(self):
        cocotb_util.run_cocotb_tests(test_batched, __file__, self.__module__)

    def test_python(self):
        value = Signal[BitVector[12]]()

        for n in (1, 2, 3, 4, 6, 12):
            batches = std.batched(value, n)

            assert len(batches) == len(value) / n

            for elem in batches:
                assert len(elem) == n

            for offset, elem in enumerate(batches):
                part = value[offset * n + n - 1 : offset * n]

                part <<= Null
                assert elem == BitVector[n](Null)
                elem <<= Full
                assert part == BitVector[n](Full)
