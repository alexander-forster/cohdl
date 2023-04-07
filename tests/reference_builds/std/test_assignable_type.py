from __future__ import annotations
import unittest

import cohdl
from cohdl import BitVector, Port, Signal, Variable, Unsigned
from cohdl import std


from cohdl_testutil import cocotb_util


class Coord(std.AssignableType):
    def __init__(self, x: Signal | Variable, y: Signal | Variable):
        self.x = x
        self.y = y

    def _assign_(self, source: Coord, mode: cohdl.AssignMode) -> None:
        self.x._assign_(source.x, mode)
        self.y._assign_(source.y, mode)


class test_assignable_type(cohdl.Entity):
    port_in_x = Port.input(Unsigned[8])
    port_in_y = Port.input(Unsigned[8])

    port_out_xa = Port.output(Unsigned[8])
    port_out_ya = Port.output(Unsigned[8])

    port_out_xb = Port.output(Unsigned[8])
    port_out_yb = Port.output(Unsigned[8])

    port_out_xc = Port.output(Unsigned[8])
    port_out_yc = Port.output(Unsigned[8])

    port_out_xd = Port.output(Unsigned[8])
    port_out_yd = Port.output(Unsigned[8])

    port_out_xe = Port.output(Unsigned[8])
    port_out_ye = Port.output(Unsigned[8])

    def architecture(self):
        inp = Coord(self.port_in_x, self.port_in_y)
        out_a = Coord(self.port_out_xa, self.port_out_ya)
        out_b = Coord(self.port_out_xb, self.port_out_yb)
        out_c = Coord(self.port_out_xc, self.port_out_yc)
        out_d = Coord(self.port_out_xd, self.port_out_yd)
        out_e = Coord(self.port_out_xe, self.port_out_ye)

        local_c = Coord.signal(Unsigned[8](), Unsigned[8]())

        @std.concurrent
        def logic():
            nonlocal out_a
            local_d = Coord.signal(Unsigned[8](), y=Unsigned[8]())

            out_a <<= inp
            out_b.next = inp
            local_c.next = inp
            out_c.next = local_c

            local_d <<= inp
            out_d.next = local_d

        @std.sequential
        def proc():
            local_e = Coord.variable(Unsigned[8](), y=Unsigned[8]())
            local_e.value = inp
            out_e.next = local_e


@cocotb_util.test()
async def testbench_simple(dut: test_assignable_type):
    for x in range(16):
        for y in range(16):
            dut.port_in_x.value = x
            dut.port_in_y.value = y
            await cocotb_util.step()

            assert dut.port_out_xa == x
            assert dut.port_out_ya == y
            assert dut.port_out_xb == x
            assert dut.port_out_yb == y
            assert dut.port_out_xc == x
            assert dut.port_out_yc == y
            assert dut.port_out_xd == x
            assert dut.port_out_yd == y
            assert dut.port_out_xe == x
            assert dut.port_out_ye == y


class Unittest(unittest.TestCase):
    def test(self):
        cocotb_util.run_cocotb_tests(test_assignable_type, __file__, self.__module__)


std.VhdlCompiler.to_string(test_assignable_type)
