from __future__ import annotations

import unittest

import cohdl
from cohdl import std, Bit, Port

from cohdl_testutil import cocotb_util

import random


class test_await_02(cohdl.Entity):
    clk = Port.input(Bit)

    inp_1 = Port.input(Bit)
    inp_2 = Port.input(Bit)

    out_1 = Port.output(Bit)
    out_2 = Port.output(Bit)
    out_push = Port.output(Bit, default=False)

    def architecture(self):
        clk = std.Clock(self.clk)

        @std.sequential(clk)
        async def proc_simple():
            self.out_1 <<= True
            self.out_2 <<= False
            await self.inp_1
            self.out_push ^= True
            self.out_1 <<= False
            self.out_2 <<= True
            await self.inp_2


class Mock:
    def __init__(self, dut):
        self.dut = dut
        self.inp_1 = False
        self.inp_2 = False

        self.out_1 = False
        self.out_2 = False
        self.out_push = False

        def gen():
            while True:
                self.out_1 = True
                self.out_2 = False
                self.out_push = False
                yield

                while not self.inp_1:
                    yield

                self.out_1 = False
                self.out_2 = True
                self.out_push = True

                yield

                self.out_push = False

                while not self.inp_2:
                    yield
                yield

        self.gen = gen()

    def set_input(self, inp_1, inp_2):
        self.dut.inp_1.value = self.inp_1 = inp_1
        self.dut.inp_2.value = self.inp_2 = inp_2

    def test_output(self):
        assert (
            self.dut.out_1.value == self.out_1
        ), f"port out_1:    {self.dut.out_1.value} != {self.out_1}"
        assert (
            self.dut.out_2.value == self.out_2
        ), f"port out_2:    {self.dut.out_2.value} != {self.out_2}"
        assert (
            self.dut.out_push.value == self.out_push
        ), f"port out_push: {self.dut.out_push.value} != {self.out_push}"

    async def step(self, seq: cocotb_util.SequentialTest):
        self.set_input(random.choice([True, False]), random.choice([True, False]))

        await seq.tick()
        next(self.gen)
        self.test_output()


@cocotb_util.test()
async def testbench_function_simple(dut: test_await_02):
    seq = cocotb_util.SequentialTest(dut.clk)

    mock = Mock(dut)

    mock.set_input(random.choice([True, False]), random.choice([True, False]))

    await seq.tick()

    for _ in range(100):
        await mock.step(seq)


class Unittest(unittest.TestCase):
    def test_function_simple(self):
        cocotb_util.run_cocotb_tests(test_await_02, __file__, self.__module__)
