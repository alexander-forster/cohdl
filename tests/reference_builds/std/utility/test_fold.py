from __future__ import annotations

import unittest

import cohdl
from cohdl import std, Unsigned, Port

from cohdl_testutil import cocotb_util


def min_pair(a, b):
    return a if a[0] < b[0] else b


def find_min(elems: tuple[int, int]):
    return std.batched_fold(min_pair, elems)


class test_fold(cohdl.Entity):

    val_a = Port.input(Unsigned[8])
    val_b = Port.input(Unsigned[8])
    val_c = Port.input(Unsigned[8])
    val_d = Port.input(Unsigned[8])
    val_e = Port.input(Unsigned[8])

    min_1 = Port.output(Unsigned[8])
    idx_1 = Port.output(Unsigned[3])

    min_2 = Port.output(Unsigned[8])
    idx_2 = Port.output(Unsigned[3])

    def architecture(self):
        values = [self.val_a, self.val_b, self.val_c, self.val_d, self.val_e]

        @cohdl.concurrent_context
        def logic():
            result_1 = std.batched_fold(
                min_pair, [(val, Unsigned[3](nr)) for nr, val in enumerate(values)]
            )

            result_2 = std.batched_fold(
                min_pair, [(val, Unsigned[3](nr)) for nr, val in enumerate(values[:-1])]
            )

            self.min_1 <<= result_1[0]
            self.idx_1 <<= result_1[1]

            self.min_2 <<= result_2[0]
            self.idx_2 <<= result_2[1]


#
# test code
#


@cocotb_util.test()
async def testbench_fold(dut: test_fold):
    gen = cocotb_util.ConstrainedGenerator(8)

    for _ in range(256):
        rnd_vals = [val.as_int() for val in gen.random(5)]
        a, b, c, d, e = rnd_vals

        dut.val_a.value = a
        dut.val_b.value = b
        dut.val_c.value = c
        dut.val_d.value = d
        dut.val_e.value = e

        await cocotb_util.step()

        rnd_vals.index(min(rnd_vals))

        assert dut.min_1.value == min(rnd_vals)
        assert rnd_vals[dut.idx_1.value] == min(rnd_vals)

        assert dut.min_2.value == min(rnd_vals[:-1])
        assert rnd_vals[:-1][dut.idx_2.value] == min(rnd_vals[:-1])


class Unittest(unittest.TestCase):
    def test_hdl(self):
        cocotb_util.run_cocotb_tests(test_fold, __file__, self.__module__)

    def test_python(self):

        gen = cocotb_util.ConstrainedGenerator(8)

        for _ in range(256):
            vals_5 = [val.as_int() for val in gen.random(5)]
            vals_4 = vals_5[::-1]

            out_1 = std.batched_fold(
                min_pair,
                [(val, Unsigned[3](nr)) for nr, val in enumerate(vals_5)],
            )

            min_1 = min(vals_5)
            min_2 = min(vals_4)

            assert out_1[0] == min_1
            assert vals_5[out_1[1]] == min_1

            out_2 = std.batched_fold(
                min_pair,
                [(val, Unsigned[3](nr)) for nr, val in enumerate(vals_4)],
            )

            assert out_2[0] == min_2
            assert vals_4[out_2[1]] == min_2
