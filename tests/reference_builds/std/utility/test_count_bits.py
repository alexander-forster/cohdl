from __future__ import annotations

import unittest

import random
import cohdl
from cohdl import std, BitVector, Port, pyeval

from cohdl_testutil import cocotb_util


w_list = [1, 2, 3, 5, 7, 8, 9, 15, 16, 17, 31, 32, 33]
batch_list = [None, 1, 2, 3, 5, 11]


@pyeval
def batch_suffix(b):
    return "" if b is None else f"_{b}"


class test_count_bits(cohdl.Entity):

    def architecture(self):

        for w in w_list:
            std.add_entity_port(self, Port.input(BitVector[w], name=f"vec_{w}"))

            for b in batch_list:
                s = batch_suffix(b)

                std.add_entity_port(
                    self, Port.output(BitVector[w.bit_length()], name=f"set_{w}{s}")
                )
                std.add_entity_port(
                    self, Port.output(BitVector[w.bit_length()], name=f"clear_{w}{s}")
                )

        tuples = [
            (
                getattr(self, f"vec_{w}"),
                {
                    b: (
                        getattr(self, f"set_{w}{batch_suffix(b)}"),
                        getattr(self, f"clear_{w}{batch_suffix(b)}"),
                    )
                    for b in batch_list
                },
            )
            for w in w_list
        ]

        @cohdl.concurrent_context
        def logic():
            for inp, outputs in tuples:

                for batch, (out_set, out_clear) in outputs.items():
                    if batch is None:
                        out_set <<= std.count_set_bits(inp)
                        out_clear <<= std.count_clear_bits(inp)
                    else:
                        out_set <<= std.count_set_bits(inp, batch_size=batch)
                        out_clear <<= std.count_clear_bits(inp, batch_size=batch)


#
# test code
#


@cocotb_util.test()
async def testbench_count_bits(dut: test_count_bits):
    for _ in range(256):
        vals = {w: random.randint(0, 2**w - 1) for w in w_list}

        for w, val in vals.items():
            getattr(dut, f"vec_{w}").value = val

        await cocotb_util.step()

        for w, val in vals.items():
            set_cnt = val.bit_count()
            clear_cnt = w - set_cnt

            for batch in batch_list:
                assert getattr(dut, f"set_{w}{batch_suffix(batch)}") == set_cnt
                assert getattr(dut, f"clear_{w}{batch_suffix(batch)}") == clear_cnt


class Unittest(unittest.TestCase):
    def test_hdl(self):
        cocotb_util.run_cocotb_tests(test_count_bits, __file__, self.__module__)
