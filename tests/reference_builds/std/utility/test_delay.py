from __future__ import annotations

import unittest
import random

import cohdl
from cohdl import std, Bit, BitVector, Unsigned, Port, Null, Full, Signal

from cohdl_testutil import cocotb_util
from collections import deque


class test_delay(cohdl.Entity):
    clk = Port.input(Bit)
    input = Port.input(BitVector[16])
    enable = Port.input(Bit)

    delay_0 = Port.output(BitVector[16])
    delay_1 = Port.output(BitVector[16])
    delay_2 = Port.output(BitVector[16])
    delay_3 = Port.output(BitVector[16])

    delay_en_0 = Port.output(BitVector[16])
    delay_en_1 = Port.output(BitVector[16])
    delay_en_2 = Port.output(BitVector[16])
    delay_en_3 = Port.output(BitVector[16])

    delay_sum = Port.output(Unsigned[16])
    delay_en_sum = Port.output(Unsigned[16])

    def architecture(self):
        @std.sequential(std.Clock(self.clk))
        def process():
            self.delay_0 <<= std.delayed(self.input, 0)
            self.delay_1 <<= std.delayed(self.input, 1, initial=Null)
            self.delay_2 <<= std.delayed(self.input, 2, initial=Full)
            self.delay_3 <<= std.delayed(self.input, 3, initial=Unsigned[16](0x1234))

            self.delay_sum <<= std.binary_fold(
                lambda a, b: a.unsigned + b.unsigned,
                std.DelayLine(self.input, 3, initial=Unsigned[16](0x1234)),
            )

            if self.enable:
                self.delay_en_0 <<= std.delayed(self.input, 0)
                self.delay_en_1 <<= std.delayed(self.input, 1, initial=Full)
                self.delay_en_2 <<= std.delayed(self.input, 2, initial=Null)
                self.delay_en_3 <<= std.delayed(
                    self.input, 3, initial=Unsigned[16](0xABCD)
                )

                self.delay_en_sum <<= std.binary_fold(
                    lambda a, b: a.unsigned + b.unsigned,
                    std.DelayLine(self.input, 3, initial=Unsigned[16](0xABCD)),
                )


#
# test code
#


@cocotb_util.test()
async def testbench_delay(dut: test_delay):
    VAL_NULL = 0
    VAL_FULL = 2**16 - 1
    VAL_1234 = 0x1234
    VAL_ABCD = 0xABCD

    dut.clk.value = False
    d_0 = deque((None,), maxlen=1), dut.delay_0
    d_1 = deque((VAL_NULL,) * 2, maxlen=2), dut.delay_1
    d_2 = deque((VAL_FULL,) * 3, maxlen=3), dut.delay_2
    d_3 = deque((VAL_1234,) * 4, maxlen=4), dut.delay_3

    d_en_0 = deque((None,), maxlen=1), dut.delay_en_0
    d_en_1 = deque((VAL_FULL,) * 2, maxlen=2), dut.delay_en_1
    d_en_2 = deque((VAL_NULL,) * 3, maxlen=3), dut.delay_en_2
    d_en_3 = deque((VAL_ABCD,) * 4, maxlen=4), dut.delay_en_3

    pairs = (d_0, d_1, d_2, d_3)
    pairs_en = (d_en_0, d_en_1, d_en_2, d_en_3)
    once_enabled = False

    for input in range(128):
        en = random.choice([True, False])
        once_enabled = once_enabled or en

        dut.clk.value = False
        dut.enable.value = en
        dut.input.value = input
        await cocotb_util.step()
        await cocotb_util.step()
        await cocotb_util.step()

        for mock, real in pairs:
            mock.popleft()
            mock.append(input)

        if en:
            for mock, real in pairs_en:
                mock.popleft()
                mock.append(input)

        dut.clk.value = True
        await cocotb_util.step()
        await cocotb_util.step()
        await cocotb_util.step()

        for mock, real in pairs:
            expected = mock[0]

            if expected is not None:
                assert real.value == expected

        expected_sum = sum(d_3[0]) % (2**16)
        assert dut.delay_sum.value == expected_sum

        if once_enabled:
            for mock, real in pairs_en:
                expected = mock[0]

                if expected is not None:
                    assert real.value == expected

            expected_sum = sum(d_en_3[0]) % (2**16)
            assert dut.delay_en_sum.value == expected_sum


class Unittest(unittest.TestCase):
    def test_hdl(self):
        cocotb_util.run_cocotb_tests(test_delay, __file__, self.__module__)
