from __future__ import annotations

import unittest
from collections import deque

import cohdl
from cohdl import std, Bit, BitVector, Port

from cohdl_testutil import cocotb_util

# same test as test_fifo_01 but with a fifo size that is not a power of 2


class test_fifo_02(cohdl.Entity):
    clk = Port.input(Bit)
    reset = Port.input(Bit)

    data_in = Port.input(BitVector[4])
    push = Port.input(Bit)

    data_out = Port.output(BitVector[4])
    front = Port.output(BitVector[4])
    pop = Port.input(Bit)

    empty = Port.output(Bit)
    full = Port.output(Bit)

    def architecture(self):
        ctx = std.SequentialContext(std.Clock(self.clk), std.Reset(self.reset))
        fifo = std.Fifo[BitVector[4], 11]()

        @std.concurrent
        def logic():
            self.front <<= fifo.front()
            self.empty <<= fifo.empty()
            self.full <<= fifo.full()

        @ctx
        def data_receiver():
            if self.push:
                fifo.push(self.data_in)

        @ctx
        def data_transmitter():
            if self.pop:
                self.data_out <<= fifo.pop()


#
# test code
#


class MockFifo:
    def __init__(self, size):
        self.size = size - 1
        self.buffer: deque[int | None] = deque([], maxlen=size - 1)
        self.last_poped = None

    def fill_count(self):
        return len(self.buffer)

    def push(self, value):
        self.buffer.append(value)

    def pop(self):
        result = self.buffer.popleft()
        self.last_poped = result
        return result

    def front(self):
        return self.buffer[0]

    def full(self):
        return len(self.buffer) == self.size

    def empty(self):
        return len(self.buffer) == 0


class FifoTester:
    def push(self, val):
        self.dut.data_in.value = val
        self.dut.push.value = True
        self.mock.push(val)

    def pop(self):
        self.dut.pop.value = True
        self.mock.pop()

    def full(self):
        assert self.dut.full.value == self.mock.full()
        return self.mock.full()

    def empty(self):
        assert self.dut.empty.value == self.mock.empty()
        return self.mock.empty()

    async def step(self):
        await self.seq.tick()
        self.dut.push.value = False
        self.dut.pop.value = False

        assert self.dut.empty.value == self.mock.empty()
        assert self.dut.full.value == self.mock.full()

        if self.mock.last_poped is not None:
            assert self.dut.data_out.value == self.mock.last_poped

    def __init__(self, dut: test_fifo_02):
        self.dut = dut
        self.seq = cocotb_util.SequentialTest(dut.clk)
        self.gen = cocotb_util.ConstrainedGenerator(4)

        self.mock = MockFifo(11)

    async def reset(self):
        self.dut.clk.value = 0
        self.dut.reset.value = True
        self.dut.push.value = False
        self.dut.pop.value = False
        self.dut.data_in.value = 0
        await self.seq.tick()
        await self.seq.tick()
        self.dut.reset.value = False
        await self.seq.tick()


@cocotb_util.test()
async def testbench_fifo_02_single_push_pop(dut: test_fifo_02):
    tester = FifoTester(dut)
    await tester.reset()

    for _ in range(100):
        val = tester.gen.random().as_int()

        tester.push(val)
        await tester.step()
        tester.pop()
        await tester.step()


@cocotb_util.test()
async def testbench_fifo_02_full_empty(dut: test_fifo_02):
    tester = FifoTester(dut)
    await tester.reset()

    for prefill_cnt in range(13):
        while not tester.full():
            tester.push(tester.gen.random().as_int())
            await tester.step()

        while not tester.empty():
            tester.pop()
            await tester.step()

        for _ in range(prefill_cnt):
            if tester.full():
                break

            tester.push(tester.gen.random().as_int())
            await tester.step()


class Unittest(unittest.TestCase):
    def test_fifo_02(self):
        cocotb_util.run_cocotb_tests(test_fifo_02, __file__, self.__module__)
