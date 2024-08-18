from __future__ import annotations

import unittest

import cohdl
from cohdl import std, Bit, BitVector, Unsigned, Port, Null, Full

import cohdl_testutil

from cohdl_testutil import cocotb_util

import cocotb
import random


@std.TemplateArg
class PairArg:
    first: type
    second: type


class Pair(std.Record[PairArg]):
    first: PairArg.first
    second: PairArg.second


class RecordEnum(std.Enum[Pair[Bit, Unsigned[3]]]):
    a = Pair[Bit, Unsigned[3]](False, Null)
    b = Pair[Bit, Unsigned[3]](False, Full)
    c = Pair[Bit, Unsigned[3]](True, Null)
    d = Pair[Bit, Unsigned[3]](True, Full)


class test_enum_04(cohdl.Entity):
    clk = Port.input(Bit)

    inp_first = Port.input(Bit)
    inp_second = Port.input(Unsigned[3])
    inp_index = Port.input(Unsigned[3])

    do_write = Port.input(BitVector[2])

    out_index = Port.input(Unsigned[3])
    out_first = Port.output(Bit)
    out_second = Port.output(Unsigned[3])

    out_pair_first = Port.output(Bit)
    out_pair_second = Port.output(Unsigned[3])

    out_is_a = Port.output(Bit)

    def architecture(self):
        clk = std.Clock(self.clk)
        ctx = std.SequentialContext(clk)

        buffer = std.Array[RecordEnum, 8](Null)

        target = std.Ref[Pair[Bit, Unsigned[3]]](
            self.out_pair_first, self.out_pair_second
        )

        @ctx
        def proc_write():
            obj = RecordEnum._underlying_(self.inp_first, self.inp_second)

            if self.do_write == "11":
                buffer[self.inp_index].raw <<= obj
            elif self.do_write[0]:
                buffer[self.inp_index].raw.first <<= self.inp_first
            elif self.do_write[1]:
                buffer[self.inp_index].raw.second <<= self.inp_second

        @std.concurrent
        def proc_read():
            nonlocal target

            elem = buffer[self.out_index]
            self.out_first <<= elem.raw.first
            self.out_second <<= elem.raw.second
            self.out_is_a <<= elem == RecordEnum.a
            target <<= elem.raw


@cocotb.test()
async def testbench_enum_04(dut: test_enum_04):
    seq = cocotb_util.SequentialTest(dut.clk)

    dut.inp_index.value = 0
    dut.inp_first.value = 0
    dut.inp_second.value = 0
    dut.do_write.value = 0
    dut.out_index.value = 0

    await seq.tick()
    buffer = [[0, 0] for _ in range(8)]

    for _ in range(128):
        inp_index = random.randint(0, 7)
        inp_first = random.randint(0, 1)
        inp_second = random.randint(0, 7)
        out_index = random.randint(0, 7)
        do_write = random.randint(0, 3)

        dut.inp_index.value = inp_index
        dut.inp_first.value = inp_first
        dut.inp_second.value = inp_second
        dut.do_write.value = do_write
        dut.out_index.value = out_index

        match do_write:
            case 0:
                pass
            case 1:
                buffer[inp_index][0] = inp_first
            case 2:
                buffer[inp_index][1] = inp_second
            case 3:
                buffer[inp_index] = [inp_first, inp_second]

        await seq.tick()

        assert dut.out_first == buffer[out_index][0]
        assert dut.out_second == buffer[out_index][1]
        assert dut.out_pair_first == buffer[out_index][0]
        assert dut.out_pair_second == buffer[out_index][1]
        assert dut.out_is_a == (buffer[out_index] == [0, 0])


class Unittest(unittest.TestCase):
    def test_enum_04(self):
        cohdl_testutil.run_cocotb_tests(test_enum_04, __file__, self.__module__)
