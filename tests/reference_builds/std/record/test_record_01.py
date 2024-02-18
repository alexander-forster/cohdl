from __future__ import annotations

import unittest

import cohdl
from cohdl import std, Bit, BitVector, Port, Unsigned, Signed

import cohdl_testutil
from cohdl_testutil.cocotb_util import ConstraindValue, ConstrainedGenerator

from cohdl_testutil import cocotb_util

import random
import cocotb


class SimpleRecord(std.Record):
    a: Bit
    b: BitVector[8]
    c: Unsigned[4]
    d: Signed[7]


class test_record_01(cohdl.Entity):
    inp_a = Port.input(Bit)
    inp_b = Port.input(BitVector[8])
    inp_c = Port.input(Unsigned[4])
    inp_d = Port.input(Signed[7])

    out_a = Port.output(Bit)
    out_b = Port.output(BitVector[8])
    out_c = Port.output(Unsigned[4])
    out_d = Port.output(Signed[7])

    serdes_a = Port.output(Bit)
    serdes_b = Port.output(BitVector[8])
    serdes_c = Port.output(Unsigned[4])
    serdes_d = Port.output(Signed[7])

    def architecture(self):
        @std.concurrent
        def logic():
            inp_record = SimpleRecord(
                a=self.inp_a, b=self.inp_b, c=self.inp_c, d=self.inp_d
            )

            sig_record = std.Signal[SimpleRecord](inp_record)

            serialized = std.to_bits(sig_record)
            deserialized = std.from_bits[SimpleRecord](serialized)

            self.out_a <<= inp_record.a
            self.out_b <<= inp_record.b
            self.out_c <<= inp_record.c
            self.out_d <<= inp_record.d

            self.serdes_a <<= deserialized.a
            self.serdes_b <<= deserialized.b
            self.serdes_c <<= deserialized.c
            self.serdes_d <<= deserialized.d


@cocotb.test()
async def testbench_record_01(dut: test_record_01):

    for a in ConstrainedGenerator(1).all():
        for b in ConstrainedGenerator(8).random(5):
            for c in ConstrainedGenerator(4).random(5):
                for d in ConstrainedGenerator(7).random(3):
                    await cocotb_util.check_concurrent(
                        [
                            (dut.inp_a, a),
                            (dut.inp_b, b),
                            (dut.inp_c, c),
                            (dut.inp_d, d),
                        ],
                        [
                            (dut.out_a, a),
                            (dut.out_b, b),
                            (dut.out_c, c),
                            (dut.out_d, d),
                            (dut.serdes_a, a),
                            (dut.serdes_b, b),
                            (dut.serdes_c, c),
                            (dut.serdes_d, d),
                        ],
                    )


class Unittest(unittest.TestCase):
    def test_record_01(self):
        cohdl_testutil.run_cocotb_tests(test_record_01, __file__, self.__module__)
