from __future__ import annotations

import unittest

import cohdl
from cohdl import std
from cohdl import Bit, BitVector, Port, Unsigned, select_with, Null, Full, enum

import cohdl_testutil

import random
import cocotb
import asyncio

asyncio.run

Axi4Light = std.axi.axi4_light.Axi4Light


class test_axi4_light(cohdl.Entity):
    inp_vector = Port.input(BitVector[16])

    clk = Port.input(Bit)
    reset = Port.input(Bit)

    read_cnt = Port.output(BitVector[4], default=cohdl.Null)
    write_cnt = Port.output(BitVector[4], default=cohdl.Null)

    def architecture(self):
        clk = std.Clock(self.clk)
        reset = std.Reset(self.reset)

        con = Axi4Light.signal(
            clk,
            reset,
            addr_width=16,
            data_width=16,
            prot_width=2,
            resp_width=2,
            strb_width=2,
            prefix="axi_",
        )

        def read_handler(addr, prot):
            self.read_cnt.unsigned <<= self.read_cnt.unsigned + 1
            return self.read_cnt, cohdl.Null

        @cohdl.sequential(clk, reset)
        async def slave_read():
            await con.handle_reads(read_handler)

        def write_handler(addr, prot, data, strb):
            self.write_cnt.unsigned <<= self.write_cnt.unsigned + 1
            return cohdl.Null

        @cohdl.sequential(clk, reset)
        async def slave_write():
            await con.handle_writes(write_handler)

        @cohdl.sequential(clk, reset)
        async def proc_simple():
            data, _ = await con.read_word(0x1234, cohdl.Null)
            await con.write_word(0x4444, data, cohdl.Full, cohdl.Null)

        async def logic():
            await ...
            await ...

        l = logic()

        @cohdl.sequential(clk, reset)
        async def asdf():
            if prescaler:
                cohdl.coroutine_step(l)


@cocotb.test()
async def testbench_function_simple(dut: test_axi4_light):
    return


class Unittest(unittest.TestCase):
    def test_register_simple(self):
        cohdl_testutil.run_cocotb_tests(test_axi4_light, __file__, self.__module__)
