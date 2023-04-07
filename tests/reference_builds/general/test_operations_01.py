import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Unsigned, select_with, Null
from cohdl import std
import random

from cohdl_testutil import cocotb_util


class simple(cohdl.Entity):
    sw = Port.input(BitVector[16])
    led = Port.output(BitVector[16])

    lsb = Port.output(Bit)
    lsb_4 = Port.output(BitVector[4])
    lsb_rest_4 = Port.output(BitVector[12])

    msb = Port.output(Bit)
    msb_4 = Port.output(BitVector[4])
    msb_rest_4 = Port.output(BitVector[12])

    a = Port.input(Unsigned[16])
    b = Port.input(Unsigned[16])
    sum = Port.output(Unsigned[16])
    dif = Port.output(Unsigned[16])
    prod = Port.output(Unsigned[32])
    prod_wide = Port.output(Unsigned[40])

    select_arg = Port.input(Bit)

    selected = Port.output(Unsigned[16])
    if_selected = Port.output(Unsigned[16])

    field_15_0 = Port.output(BitVector[16])
    field_11_4 = Port.output(BitVector[8])
    field_15_12 = Port.output(BitVector[4])
    field_3_0 = Port.output(BitVector[4])

    def architecture(self):
        @std.concurrent
        def logic():
            self.led[0] <<= self.sw[0]
            self.lsb <<= self.sw.lsb()
            self.lsb_4 <<= self.sw.lsb(4)
            self.lsb_rest_4 <<= self.sw.lsb(rest=4)

            self.msb <<= self.sw.msb()
            self.msb_4 <<= self.sw.msb(4)
            self.msb_rest_4 <<= self.sw.msb(rest=4)

            self.field_15_0 <<= self.sw[15:0]
            self.field_11_4 <<= self.sw[11:4]
            self.field_15_12 <<= self.sw[15:12]
            self.field_3_0 <<= self.sw[3:0]

            self.led <<= self.sw
            self.sum <<= self.a + self.b
            self.dif <<= self.b - self.a
            self.prod <<= self.a * self.b
            self.prod_wide <<= self.a * self.b

            self.selected <<= select_with(
                self.select_arg, {Bit(0): self.a, Bit(1): self.b}, Null
            )

            self.if_selected <<= self.a if self.select_arg else self.b


@cocotb_util.test()
async def testbench_simple(dut: simple):
    value_gen = cocotb_util.ConstrainedGenerator(16)

    for i in range(100):
        val = value_gen.random()
        a = value_gen.random()
        b = value_gen.random()

        a, b = sorted([a, b])

        sum = (a + b).resize(16)
        dif = (b - a).resize(16)
        prod = a * b

        cocotb_util.assign(dut.sw, val)
        cocotb_util.assign(dut.a, a)
        cocotb_util.assign(dut.b, b)
        cocotb_util.assign(dut.select_arg, 0)

        await cocotb_util.step()
        await cocotb_util.step()

        assert dut.lsb == val[0], "assignment of lsb not working"
        assert dut.lsb_4 == val[0:3], "assignment of lsb_4 not working"
        assert dut.lsb_rest_4 == val[0:11], "assignment of lsb_rest_4 not working"

        assert dut.msb == val[-1], "assignment of msb not working"
        assert dut.msb_4 == val[12:15], f"assignment of msb_4 not working"
        assert dut.msb_rest_4 == val[4:15], "assignment of msb_rest_4 not working"

        assert dut.led == val.value, f"output q was incorrect on the {i}th cycle"
        assert dut.sum == sum.value, f"sum {dut.sum} != {sum}  with {a=}, {b=}"
        assert dut.dif == dif.value, f"difference {dut.dif} != {dif}"
        assert dut.prod == prod.value, f"prod {dut.prod} != {prod} with {a=}  {b=}"
        assert dut.prod_wide == prod.value
        assert (
            dut.selected == a
        ), f"selected output {dut.selected} does not match expected value {bin(a)}"
        assert dut.if_selected == b

        assert dut.field_15_0 == val
        assert dut.field_11_4 == val[4:11]
        assert dut.field_15_12 == val[12:15]
        assert dut.field_3_0 == val[0:3]

        cocotb_util.assign(dut.select_arg, 1)

        await cocotb_util.step()

        assert (
            dut.selected == b
        ), f"selected output {dut.selected} doest not match expected value {bin(b)}"
        assert dut.if_selected == a


class Unittest(unittest.TestCase):
    def test_concurrent(self):
        cocotb_util.run_cocotb_tests(simple, __file__, self.__module__)


std.VhdlCompiler.to_string(simple)
