from __future__ import annotations

import unittest

import cohdl
from cohdl import std, BitVector, Port, Full

from cohdl_testutil import cocotb_util


class test_count(cohdl.Entity):
    val_a = Port.input(BitVector[6])
    val_b = Port.input(BitVector[6])
    val_c = Port.input(BitVector[6])
    val_d = Port.input(BitVector[6])
    val_e = Port.input(BitVector[6])
    val_f = Port.input(BitVector[6])

    count_0 = Port.output(BitVector[3])
    count_1 = Port.output(BitVector[3])
    count_2 = Port.output(BitVector[3])
    count_3 = Port.output(BitVector[3])

    count_empty = Port.output(BitVector[1])
    count_one = Port.output(BitVector[1])

    def architecture(self):
        values = [
            self.val_a,
            self.val_b,
            self.val_c,
            self.val_d,
            self.val_e,
            self.val_f,
        ]

        @cohdl.concurrent_context
        def logic():

            self.count_0 <<= std.count(values, std.zeros(6))
            self.count_1 <<= std.count(values[1:], Full)
            self.count_2 <<= std.count(values, check=lambda a: a[2])
            self.count_3 <<= std.count(values[:-1], check=lambda x: x[0] & x[1])

            self.count_empty <<= std.count([], value=5)
            self.count_one <<= std.count((self.val_d,), check=lambda x: x[5] @ x[3])


# print(std.VhdlCompiler.to_string(test_count))

#
# test code
#


@cocotb_util.test()
async def testbench_count(dut: test_count):
    gen = cocotb_util.ConstrainedGenerator(6)

    for _ in range(256):
        uvals = [val.as_int() for val in gen.random(6)]
        a, b, c, d, e, f = uvals

        dut.val_a.value = a
        dut.val_b.value = b
        dut.val_c.value = c
        dut.val_d.value = d
        dut.val_e.value = e
        dut.val_f.value = f

        await cocotb_util.step()

        assert dut.count_0 == uvals.count(0) == std.count(uvals, 0)
        assert (
            dut.count_1
            == uvals[1:].count(63)
            == std.count(uvals[1:], value=63).to_int()
        )
        assert (
            dut.count_2
            == len([v for v in uvals if v & 4])
            == std.count(uvals, check=lambda x: x & 4)
        )
        assert (
            dut.count_3
            == len([v for v in uvals[:-1] if v & 3 == 3])
            == std.count(uvals[:-1], check=lambda x: x & 3 == 3)
        )

        assert dut.count_empty == 0 == std.count([], value=11)
        assert (
            dut.count_one
            == (1 if d & 40 else 0)
            == std.count((d,), check=lambda d: d & 40)
        )


class Unittest(unittest.TestCase):
    def test_hdl(self):
        cocotb_util.run_cocotb_tests(test_count, __file__, self.__module__)
