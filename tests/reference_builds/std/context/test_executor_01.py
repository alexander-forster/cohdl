from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, Port, Signal, Unsigned, Variable
from cohdl import std

from cohdl_testutil import cocotb_util


async def add_args(a: Unsigned[32], b: Unsigned[32] | int):
    return a + b


class test_executor_01(cohdl.Entity):
    clk = Port.input(Bit)
    reset = Port.input(Bit)
    start = Port.input(Bit)

    inp_1 = Port.input(Unsigned[32])
    inp_2 = Port.input(Unsigned[32])
    inp_3 = Port.input(Unsigned[32])

    result_parallel = Port.output(Unsigned[32])
    result_before = Port.output(Unsigned[32])
    result_after = Port.output(Unsigned[32])

    is_ready = Port.output(Bit)

    def architecture(self):
        ctx = std.SequentialContext(
            std.Clock(self.clk),
            std.Reset(self.reset),
        )

        S = Signal[Unsigned[32]]
        V = Variable[Unsigned[32]]

        exec_parallel = std.Executor.make_parallel(ctx, add_args, S(), S(), S())
        exec_after = std.Executor.make_after(add_args, S(), V(), b=V())
        exec_before = std.Executor.make_before(add_args, V(), a=S(), b=S())

        std.concurrent_eval(self.is_ready, exec_parallel.ready)

        @ctx
        async def proc_parallel():
            await self.start
            exec_parallel.start(self.inp_1, self.inp_2)
            await exec_parallel.ready()
            self.result_parallel <<= exec_parallel.result()

            await self.start
            self.result_parallel <<= await exec_parallel.exec(self.inp_2, self.inp_3)

        @ctx
        async def proc_after():
            await self.start
            exec_after.start(self.inp_1, b=self.inp_2)
            await exec_after.ready()
            self.result_after <<= exec_after.result()

            await self.start
            self.result_after <<= await exec_after.exec(self.inp_2, b=self.inp_3)

        @ctx(executors=[exec_before])
        async def proc_before():
            await self.start
            exec_before.start(a=self.inp_1, b=self.inp_2)
            await exec_before.ready()
            self.result_before <<= exec_before.result()

            await self.start
            self.result_before <<= await exec_before.exec(a=self.inp_2, b=self.inp_3)


#
# test code
#


@cocotb_util.test()
async def testbench_executor_01(dut: test_executor_01):
    gen = cocotb_util.ConstrainedGenerator(32)

    seq = cocotb_util.SequentialTest(dut.clk)
    dut.start.value = False
    dut.reset.value = True
    dut.inp_1.value = 0
    dut.inp_2.value = 0
    dut.inp_3.value = 0
    await seq.tick()
    await seq.tick()
    dut.reset.value = False

    for _ in range(4):
        await seq.tick()

        for inp_1, inp_2, inp_3 in zip(gen.random(32), gen.random(32), gen.random(32)):

            async def runTest(expected):
                dut.start.value = True
                dut.inp_1.value = inp_1.as_int()
                dut.inp_2.value = inp_2.as_int()
                dut.inp_3.value = inp_3.as_int()
                await seq.tick()
                dut.start.value = False
                dut.inp_1.value = 0
                dut.inp_2.value = 0
                dut.inp_3.value = 0
                await seq.tick()
                assert dut.result_after.value == expected
                assert dut.result_before.value == expected
                await seq.tick()
                assert dut.result_after.value == expected
                assert dut.result_before.value == expected
                assert dut.result_parallel.value == expected

            await runTest((inp_1 + inp_2).as_int())
            await runTest((inp_2 + inp_3).as_int())


class Unittest(unittest.TestCase):
    def test_executor_01(self):
        cocotb_util.run_cocotb_tests(
            test_executor_01,
            __file__,
            self.__module__,
        )
