from __future__ import annotations

import unittest

import cohdl
from cohdl import std, BitVector, Unsigned, Port

from cohdl_testutil import cocotb_util

T = std.TemplateArg.Type


class WrappedVal(std.Record[T]):
    val: T

    def __lt__(self, other: WrappedVal):
        return self.val < other.val


Wu8 = WrappedVal[Unsigned[8]]


class test_clamp(cohdl.Entity):
    inp_val = Port.input(BitVector[8])
    inp_low = Port.input(BitVector[8])
    inp_high = Port.input(BitVector[8])

    out_a = Port.output(BitVector[8])
    out_b = Port.output(BitVector[8])
    out_c = Port.output(BitVector[8])
    out_d = Port.output(BitVector[8])

    def architecture(self):

        @cohdl.concurrent_context
        def logic():

            val_u = self.inp_val.unsigned
            val_s = self.inp_val.signed

            self.out_a <<= std.clamp(val_u, 0, 37)
            self.out_b <<= std.clamp(val_s, -3, Unsigned[7](111))
            self.out_c <<= std.clamp(Wu8(val_u), Wu8(77), Wu8(201)).val
            self.out_d <<= std.clamp(
                Wu8(val_u), Wu8(13), Wu8(150), cmp=lambda a, b: a.val > b.val
            ).val


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


def clamp(val, a, b, cmp=lambda a, b: a < b):
    if cmp(val, a):
        return a
    if cmp(b, val):
        return b
    return val


@cocotb_util.test()
async def testbench_clamp(dut: test_clamp):
    gen = cocotb_util.ConstrainedGenerator(8)

    for val in range(256):
        sval = to_signed(val)

        dut.inp_val.value = val

        await cocotb_util.step()

        assert dut.out_a == clamp(val, 0, 37) == std.clamp(val, 0, 37)
        assert (
            to_signed(dut.out_b)
            == clamp(sval, -3, 111)
            == std.clamp(sval, -3, Unsigned[7](111))
        )
        assert dut.out_c == clamp(val, 77, 201) == std.clamp(Wu8(val), 77, Wu8(201)).val
        assert (
            dut.out_d
            == clamp(val, 13, 150, cmp=lambda a, b: a > b)
            == std.clamp(Wu8(val), 13, Wu8(150), cmp=lambda a, b: a.val > b.val).val
        )


class Unittest(unittest.TestCase):
    def test_hdl(self):
        cocotb_util.run_cocotb_tests(test_clamp, __file__, self.__module__)
