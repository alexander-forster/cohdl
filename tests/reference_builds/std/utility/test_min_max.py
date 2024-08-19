from __future__ import annotations

import unittest

import cohdl
from cohdl import std, BitVector, Signed, Unsigned, Port

from cohdl_testutil import cocotb_util


class test_min_max(cohdl.Entity):
    val_a = Port.input(BitVector[8])
    val_b = Port.input(Signed[8])
    val_c = Port.input(Unsigned[8])
    val_d = Port.input(BitVector[8])
    val_e = Port.input(Signed[8])
    val_f = Port.input(Unsigned[8])

    min_1 = Port.output(BitVector[8])
    max_1 = Port.output(BitVector[8])

    min_2 = Port.output(BitVector[8])
    max_2 = Port.output(BitVector[8])

    min_3 = Port.output(BitVector[8])
    max_3 = Port.output(BitVector[8])

    min_4 = Port.output(BitVector[8])
    max_4 = Port.output(BitVector[8])
    min_4n = Port.output(Unsigned[3])
    max_4n = Port.output(Unsigned[3])

    min_5 = Port.output(BitVector[8])
    max_5 = Port.output(BitVector[8])
    min_5n = Port.output(Unsigned[3])
    max_5n = Port.output(Unsigned[3])

    def architecture(self):
        values = [
            self.val_a,
            self.val_b,
            self.val_c,
            self.val_d,
            self.val_e,
            self.val_f,
        ]

        a, b, c, d, e, f = values

        nvalues = [(Unsigned[3](n), v.signed) for n, v in enumerate(values)]
        na, nb, nc, nd, ne, nf = nvalues

        @cohdl.concurrent_context
        def logic():
            self.min_1 <<= std.minimum(a.unsigned, b.unsigned)
            self.max_1 <<= std.maximum(a.unsigned, b.unsigned)

            self.min_2 <<= std.minimum((b, e))
            self.max_2 <<= std.maximum([c, f])

            self.min_3 <<= std.minimum((a,))
            self.max_3 <<= std.maximum([d])

            min_4nv = std.minimum(nvalues, key=lambda a: a[1])
            max_4nv = std.maximum(na, nb, nc, nd, ne, nf, key=lambda a: a[1])

            self.min_4n <<= min_4nv[0]
            self.min_4 <<= min_4nv[1]

            self.max_4n <<= max_4nv[0]
            self.max_4 <<= max_4nv[1]

            #
            #
            #

            min_5nv = std.minimum(
                na,
                nb,
                nc,
                nd,
                ne,
                key=lambda a: a[1],
                cmp=lambda a, b: (a >> 1) < (b >> 1),
            )
            max_5nv = std.maximum(
                nvalues[1:], cmp=lambda a, b: (a[1] >> 2) > (b[1] >> 2)
            )

            self.min_5n <<= min_5nv[0]
            self.min_5 <<= min_5nv[1]

            self.max_5n <<= max_5nv[0]
            self.max_5 <<= max_5nv[1]


#
# test code
#


def to_signed(vals):
    if isinstance(vals, (list, tuple)):
        return [to_signed(val) for val in vals]

    if isinstance(vals, int):
        return vals if vals < 128 else (vals - 256)
    else:
        return to_signed(int(vals))


@cocotb_util.test()
async def testbench_min_max(dut: test_min_max):
    gen = cocotb_util.ConstrainedGenerator(8)

    for _ in range(256):
        uvals = [val.as_int() for val in gen.random(6)]
        a, b, c, d, e, f = uvals

        svals = to_signed(uvals)
        sa, sb, sc, sd, se, sf = svals

        nvals = [(n, s) for n, s in enumerate(svals)]

        dut.val_a.value = a
        dut.val_b.value = b
        dut.val_c.value = c
        dut.val_d.value = d
        dut.val_e.value = e
        dut.val_f.value = f

        await cocotb_util.step()

        assert dut.min_1 == min(a, b) == std.minimum(a, b)
        assert dut.max_1 == max(a, b) == std.maximum(a, b)

        assert to_signed(dut.min_2) == min(sb, se) == std.minimum(sb, se)
        assert dut.max_2 == max(c, f) == std.maximum(c, f)

        assert dut.min_3 == a == std.minimum((a,))
        assert dut.max_3 == d == std.maximum([d])

        min_4nv = min(nvals, key=lambda a: a[1])
        max_4nv = max(nvals, key=lambda a: a[1])

        min_4nv_std = std.minimum(nvals, key=lambda a: a[1])
        max_4nv_std = std.maximum(nvals, key=lambda a: a[1])

        assert to_signed(dut.min_4) == min_4nv[1] == min_4nv_std[1]
        assert dut.min_4n == min_4nv[0] == min_4nv_std[0]

        assert to_signed(dut.max_4) == max_4nv[1] == max_4nv_std[1]
        assert dut.max_4n == max_4nv[0] == max_4nv_std[0]

        min_5nv = min(nvals[:-1], key=lambda a: a[1] >> 1)
        max_5nv = max(nvals[1:], key=lambda a: a[1] >> 2)

        min_5nv_std = std.minimum(
            nvals[:-1], key=lambda a: a[1] >> 1, cmp=lambda a, b: a < b
        )
        max_5nv_std = std.maximum(nvals[1:], cmp=lambda a, b: (a[1] >> 2) > (b[1] >> 2))

        assert to_signed(dut.min_5) == min_5nv[1] == min_5nv_std[1]
        assert dut.min_5n == min_5nv[0] == min_5nv_std[0]

        assert to_signed(dut.max_5) == max_5nv[1] == max_5nv_std[1]
        assert dut.max_5n == max_5nv[0] == max_5nv_std[0]


class Unittest(unittest.TestCase):
    def test_hdl(self):
        cocotb_util.run_cocotb_tests(test_min_max, __file__, self.__module__)
