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
    min_2idx = Port.output(BitVector[2])
    max_2idx = Port.output(BitVector[2])
    min_2elem = Port.output(BitVector[8])
    max_2elem = Port.output(BitVector[8])
    min_2elem_idx = Port.output(BitVector[2])
    max_2elem_idx = Port.output(BitVector[2])

    min_3 = Port.output(BitVector[8])
    max_3 = Port.output(BitVector[8])
    min_3idx = Port.output(BitVector[1])
    max_3idx = Port.output(BitVector[1])
    min_3elem = Port.output(BitVector[8])
    max_3elem = Port.output(BitVector[8])
    min_3elem_idx = Port.output(BitVector[1])
    max_3elem_idx = Port.output(BitVector[1])

    min_4 = Port.output(BitVector[8])
    max_4 = Port.output(BitVector[8])
    min_4n = Port.output(Unsigned[3])
    max_4n = Port.output(Unsigned[3])
    min_4idx = Port.output(BitVector[3])
    max_4idx = Port.output(BitVector[3])
    min_4elem = Port.output(BitVector[8])
    max_4elem = Port.output(BitVector[8])
    min_4elem_idx = Port.output(BitVector[3])
    max_4elem_idx = Port.output(BitVector[3])

    min_5 = Port.output(BitVector[8])
    max_5 = Port.output(BitVector[8])
    min_5n = Port.output(Unsigned[3])
    max_5n = Port.output(Unsigned[3])
    min_5idx = Port.output(BitVector[3])
    max_5idx = Port.output(BitVector[3])
    min_5elem = Port.output(BitVector[8])
    max_5elem = Port.output(BitVector[8])
    min_5elem_idx = Port.output(BitVector[3])
    max_5elem_idx = Port.output(BitVector[3])

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
            self.min_2idx <<= std.min_index((b, e))
            self.max_2idx <<= std.max_index([c, f])
            min2_idx, min_2elem = std.min_element((b, e))
            max2_idx, max_2elem = std.max_element([c, f])
            self.min_2elem_idx <<= min2_idx
            self.min_2elem <<= min_2elem
            self.max_2elem_idx <<= max2_idx
            self.max_2elem <<= max_2elem

            self.min_3 <<= std.minimum((a,))
            self.max_3 <<= std.maximum([d])
            self.min_3idx <<= std.min_index((a,))
            self.max_3idx <<= std.max_index([d])
            min3_idx, min_3elem = std.min_element((a,))
            max3_idx, max_3elem = std.max_element([d])
            self.min_3elem_idx <<= min3_idx
            self.min_3elem <<= min_3elem
            self.max_3elem_idx <<= max3_idx
            self.max_3elem <<= max_3elem

            min_4nv = std.minimum(nvalues, key=lambda a: a[1])
            max_4nv = std.maximum(na, nb, nc, nd, ne, nf, key=lambda a: a[1])

            self.min_4n <<= min_4nv[0]
            self.min_4 <<= min_4nv[1]

            self.max_4n <<= max_4nv[0]
            self.max_4 <<= max_4nv[1]

            self.min_4idx <<= std.min_index(nvalues, key=lambda a: a[1])
            self.max_4idx <<= std.max_index(nvalues, key=lambda a: a[1])

            min4_elem = std.min_element(nvalues, key=lambda a: a[1])
            max4_elem = std.max_element(nvalues, key=lambda a: a[1])

            self.min_4elem_idx <<= min4_elem[0]
            self.min_4elem <<= min4_elem[1][1]
            self.max_4elem_idx <<= max4_elem[0]
            self.max_4elem <<= max4_elem[1][1]

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

            self.min_5idx <<= std.min_index(
                nvalues[:-1], key=lambda a: a[1], cmp=lambda a, b: (a >> 1) < (b >> 1)
            )
            self.max_5idx <<= std.max_index(
                nvalues[1:], cmp=lambda a, b: (a[1] >> 2) > (b[1] >> 2)
            )

            min5_elem = std.min_element(
                nvalues[:-1], cmp=lambda a, b: (a[1] >> 1) < (b[1] >> 1)
            )
            max5_elem = std.max_element(
                nvalues[1:], key=lambda a: a[1], cmp=lambda a, b: (a >> 2) > (b >> 2)
            )

            self.min_5elem_idx <<= min5_elem[0]
            self.min_5elem <<= min5_elem[1][1]
            self.max_5elem_idx <<= max5_elem[0]
            self.max_5elem <<= max5_elem[1][1]


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

        # minmax_1

        assert dut.min_1 == min(a, b) == std.minimum(a, b)
        assert dut.max_1 == max(a, b) == std.maximum(a, b)

        # minmax_2

        assert to_signed(dut.min_2) == min(sb, se) == std.minimum(sb, se)
        assert dut.max_2 == max(c, f) == std.maximum(c, f)
        assert dut.min_2idx == [sb, se].index(min(sb, se)) == std.min_index([sb, se])
        assert dut.max_2idx == [c, f].index(max(c, f)) == std.max_index([c, f])
        assert to_signed(dut.min_2elem) == min(sb, se)
        assert dut.max_2elem == max(c, f)

        min2elem = std.min_element((sb, se))
        max2elem = std.max_element((c, f))

        assert dut.min_2elem_idx == [sb, se].index(min(sb, se)) == min2elem[0]
        assert dut.max_2elem_idx == [c, f].index(max(c, f)) == max2elem[0]
        assert to_signed(dut.min_2elem) == min2elem[1]
        assert dut.max_2elem == max2elem[1]

        # minmax_3

        assert dut.min_3 == a == std.minimum((a,))
        assert dut.max_3 == d == std.maximum([d])
        assert dut.min_3idx == 0 == std.min_index((a,))
        assert dut.max_3idx == 0 == std.max_index([d])

        min3elem = std.min_element((a,))
        max3elem = std.max_element([d])

        assert dut.min_3elem_idx == 0 == min3elem[0]
        assert dut.max_3elem_idx == 0 == max3elem[0]
        assert dut.min_3elem == a == min3elem[1]
        assert dut.max_3elem == d == max3elem[1]

        # minmax_4

        l4 = lambda a: a[1]

        min_4nv = min(nvals, key=l4)
        max_4nv = max(nvals, key=l4)

        min_4nv_std = std.minimum(nvals, key=l4)
        max_4nv_std = std.maximum(nvals, key=l4)

        assert to_signed(dut.min_4) == min_4nv[1] == min_4nv_std[1]
        assert dut.min_4n == min_4nv[0] == min_4nv_std[0]

        assert to_signed(dut.max_4) == max_4nv[1] == max_4nv_std[1]
        assert dut.max_4n == max_4nv[0] == max_4nv_std[0]

        min_4 = min(svals)
        min_4idx = svals.index(min_4)
        max_4 = max(svals)
        max_4idx = svals.index(max_4)
        min_4elem = std.min_element(nvals, key=l4)
        max_4elem = std.max_element(nvals, key=l4)

        assert dut.min_4idx == std.min_index(nvals, key=l4).to_int() == min_4idx
        assert dut.min_4elem_idx == min_4elem[0] == min_4idx
        assert to_signed(dut.min_4elem) == min_4elem[1][1] == min_4

        assert dut.max_4idx == std.max_index(nvals, key=l4).to_int() == max_4idx
        assert dut.max_4elem_idx == max_4elem[0] == max_4idx
        assert to_signed(dut.max_4elem) == max_4elem[1][1] == max_4

        # minmax_5

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

        #

        l5a = lambda a, b: (a >> 1) < (b >> 1)
        l5b = lambda a, b: (a[1] >> 2) > (b[1] >> 2)
        l5c = lambda a, b: (a[1] >> 1) < (b[1] >> 1)
        l5d = lambda a, b: (a >> 2) > (b >> 2)

        min_5 = min(svals[:-1], key=lambda a: a >> 1)
        min_5idx = svals[:-1].index(min_5)
        max_5 = max(svals[1:], key=lambda a: a >> 2)
        max_5idx = svals[1:].index(max_5)
        min_5elem = std.min_element(nvals[:-1], cmp=l5c)
        max_5elem = std.max_element(nvals[1:], key=l4, cmp=l5d)

        assert (
            dut.min_5idx
            == std.min_index(nvals[:-1], key=l4, cmp=l5a).to_int()
            == min_5idx
        )
        assert dut.min_5elem_idx == min_5elem[0] == min_5idx
        assert to_signed(dut.min_5elem) == min_5elem[1][1] == min_5
        assert dut.max_5idx == std.max_index(nvals[1:], cmp=l5b).to_int() == max_5idx
        assert dut.max_5elem_idx == max_5elem[0] == max_5idx
        assert to_signed(dut.max_5elem) == max_5elem[1][1] == max_5


class Unittest(unittest.TestCase):
    def test_hdl(self):
        cocotb_util.run_cocotb_tests(test_min_max, __file__, self.__module__)
