import unittest

import cohdl
from cohdl import Bit, Port, Unsigned
from cohdl import std

from cohdl_testutil import cocotb_util


class IntClass:
    def __init__(self, start_val):
        self.val = start_val

    def __iadd__(self, other):
        self.val += other
        return self

    def __add__(self, other):
        return IntClass(self.val + other)


class IncOnExit:
    def __init__(self, val):
        self.val = val

    async def __aenter__(self):
        await std.wait_for(1)

    async def __aexit__(self, a, b, c):
        await std.wait_for(1)
        self.val <<= self.val + 1
        await std.wait_for(1)


class IncOnExitMock:
    def __init__(self, val):
        self.val = val

    def aenter(self):
        yield

    def aexit(self):
        yield
        self.val += 1
        yield


async def callback(counter, cond, result):
    async with IncOnExit(counter):
        if cond == 0:
            result <<= counter + 1
            return

    if cond == 6 or cond == 11:
        if cond == 11:
            async with IncOnExit(counter):
                result <<= counter + 17
                return
        result <<= counter + 4
        return

    async with IncOnExit(counter), IncOnExit(counter):
        if cond == 7 or cond == 8:
            result <<= counter + 11
            return

        if cond == 4:
            result <<= counter + 1
            return

    if cond == 13:
        result <<= counter + 7
        return

    result <<= counter + 13


def callback_mock(counter, cond, result):
    a = IncOnExitMock(counter)
    yield from a.aenter()

    if cond == 0:
        result.val = counter.val + 1
        yield from a.aexit()
        return

    yield from a.aexit()

    if cond == 6 or cond == 11:
        if cond == 11:
            yield from a.aenter()
            result.val = counter.val + 17
            yield from a.aexit()
            return

        result.val = counter.val + 4
        return

    yield from a.aenter()
    yield from a.aenter()

    if cond == 7 or cond == 8:
        result.val = counter.val + 11
        yield from a.aexit()
        yield from a.aexit()
        return

    if cond == 4:
        result.val = counter.val + 1
        yield from a.aexit()
        yield from a.aexit()
        return

    yield from a.aexit()
    yield from a.aexit()

    if cond == 13:
        result.val = counter.val + 7
        return

    result.val = counter.val + 13
    return


class test_context_manager_04(cohdl.Entity):
    clk = Port.input(Bit)
    reset = Port.input(Bit)
    start = Port.input(Bit)

    condition = Port.input(Unsigned[8])
    result = Port.output(Unsigned[16])
    counter = Port.output(Unsigned[16])

    def architecture(self):
        @std.sequential(std.Clock(self.clk), std.Reset(self.reset))
        async def proc():
            self.counter <<= 0
            self.result <<= 0
            await self.start
            await callback(self.counter, self.condition, self.result)


#
# test code
#

import asyncio


@cocotb_util.test()
async def testbench_context_manager_04(dut: test_context_manager_04):
    seq = cocotb_util.SequentialTest(dut.clk)

    dut.reset.value = True
    dut.start.value = False
    await seq.tick()
    dut.reset.value = False

    for condition in range(16):
        dut.start.value = False
        dut.condition.value = condition

        counter = IntClass(0)
        result = IntClass(0)

        gen = callback_mock(counter, condition, result)

        await seq.tick(10)
        dut.start.value = True

        done = False

        while not done:
            try:
                next(gen)
            except StopIteration:
                done = True

            await seq.tick()
            dut.start.value = False
            assert counter.val == dut.counter.value
            assert result.val == dut.result.value

        await seq.tick()
        assert dut.result.value == 0
        assert dut.counter.value == 0


class Unittest(unittest.TestCase):
    def test_base(self):
        # test, that async-with works when no delay is placed in __aenter__ or __aexit__
        cocotb_util.run_cocotb_tests(test_context_manager_04, __file__, self.__module__)
