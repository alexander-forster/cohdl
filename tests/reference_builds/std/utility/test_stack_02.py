from __future__ import annotations

from collections import deque

import os
import unittest
import cohdl
import random
from cohdl import std, Bit, Port, Unsigned

from cohdl_testutil import cocotb_util

STACK_DEPTH = eval(os.getenv("cohdl_test_STACK_DEPTH", "None"))


class RecA(std.Record):
    a: Bit
    b: std.Array[Bit, 3]


def gen_entity():

    class test_stack_02(cohdl.Entity):
        clk = Port.input(Bit)
        reset = Port.input(Bit)

        inp_a = Port.input(Bit)
        inp_b0 = Port.input(Bit)
        inp_b1 = Port.input(Bit)
        inp_b2 = Port.input(Bit)

        inp_push = Port.input(Bit)
        inp_pop = Port.input(Bit)
        inp_reset = Port.input(Bit)

        out_empty = Port.output(Bit, default=True)
        out_full = Port.output(Bit, default=False)
        out_size = Port.output(Unsigned[4], default=0)

        out_a = Port.output(Bit, default=False)
        out_b0 = Port.output(Bit, default=False)
        out_b1 = Port.output(Bit, default=False)
        out_b2 = Port.output(Bit, default=False)

        out_front_a = Port.output(Bit, default=False)
        out_front_b0 = Port.output(Bit, default=False)
        out_front_b1 = Port.output(Bit, default=False)
        out_front_b2 = Port.output(Bit, default=False)

        def architecture(self):
            ctx = std.SequentialContext(std.Clock(self.clk), std.Reset(self.reset))

            stack = std.Stack[RecA, STACK_DEPTH](mode=std.StackMode.DROP_OLD)

            @std.sequential
            def logic():
                self.out_empty <<= stack.empty()
                self.out_full <<= stack.full()
                self.out_size <<= stack.size()

                front = stack.front()

                self.out_front_a <<= front.a
                x, y, z = front.b

                self.out_front_b0 <<= x
                self.out_front_b1 <<= y
                self.out_front_b2 <<= z

            @ctx
            def proc_stack_02():
                if self.inp_push:
                    stack.push(
                        RecA(a=self.inp_a, b=[self.inp_b0, self.inp_b1, self.inp_b2])
                    )

                if self.inp_pop:
                    data = stack.pop()

                    _, y, z = data.b

                    self.out_a <<= data.a
                    self.out_b0 <<= data.b[0]
                    self.out_b1 <<= y
                    self.out_b2 <<= z

                if self.inp_reset:
                    stack.reset()

    return test_stack_02


#
# test code
#


@cocotb_util.test()
async def testbench_stack_02(dut):
    seq = cocotb_util.SequentialTest(dut.clk)
    dut.reset.value = False
    dut.clk.value = False
    dut.inp_a.value = 0
    dut.inp_b0.value = 0
    dut.inp_b1.value = 0
    dut.inp_b2.value = 0
    dut.inp_pop.value = 0
    dut.inp_push.value = 0
    dut.inp_reset.value = 0

    buffer = deque([], STACK_DEPTH)

    def get_val(front=False):
        if front:
            a = dut.out_front_a.value
            b0 = dut.out_front_b0.value
            b1 = dut.out_front_b1.value
            b2 = dut.out_front_b2.value
        else:
            a = dut.out_a.value
            b0 = dut.out_b0.value
            b1 = dut.out_b1.value
            b2 = dut.out_b2.value

        return (a) | (b0 << 1) | (b1 << 2) | (b2 << 3)

    def check():
        assert dut.out_empty == (len(buffer) == 0)
        assert dut.out_full == (len(buffer) == STACK_DEPTH)
        assert dut.out_size == len(buffer)

    async def push(value):
        buffer.append(value)
        dut.inp_a.value = (value >> 0) & 1
        dut.inp_b0.value = (value >> 1) & 1
        dut.inp_b1.value = (value >> 2) & 1
        dut.inp_b2.value = (value >> 3) & 1
        dut.inp_push.value = True
        await seq.tick()
        dut.inp_push.value = False

        assert get_val(front=True) == value
        check()

    async def pop():
        if len(buffer) == 0:
            return

        expected = buffer.pop()

        dut.inp_pop.value = True
        await seq.tick()
        dut.inp_pop.value = False

        assert get_val() == expected
        check()
        return expected

    async def reset(soft=False):
        if soft:
            dut.inp_reset.value = True
        else:
            dut.reset.value = True

        await seq.tick()

        buffer.clear()
        check()

        dut.inp_reset.value = False
        dut.reset.value = False

    await seq.tick()

    for _ in range(10):
        await push(random.randint(0, 15))

    while len(buffer):
        await pop()

    for _ in range(3):
        await push(random.randint(0, 15))
    await pop()

    await reset()

    for _ in range(10):
        await push(random.randint(0, 15))

    await reset(soft=True)

    for _ in range(64):
        for _ in range(random.randint(0, 3)):
            await push(random.randint(0, 15))

        for _ in range(random.randint(0, 2)):
            await pop()

    for _ in range(64):
        for _ in range(random.randint(0, 2)):
            await push(random.randint(0, 15))

        for _ in range(random.randint(0, 3)):
            await pop()


class Unittest(unittest.TestCase):
    def test_stack_02_depth_5(self):
        global STACK_DEPTH
        STACK_DEPTH = 5

        cocotb_util.run_cocotb_tests(
            gen_entity(),
            __file__,
            self.__module__,
            extra_env={"cohdl_test_STACK_DEPTH": "5"},
        )

    def test_stack_02_depth_8(self):
        global STACK_DEPTH
        STACK_DEPTH = 8

        cocotb_util.run_cocotb_tests(
            gen_entity(),
            __file__,
            self.__module__,
            extra_env={"cohdl_test_STACK_DEPTH": "8"},
        )
