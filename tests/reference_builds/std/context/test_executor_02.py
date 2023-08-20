from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Signal, Unsigned, Variable
from cohdl import std

from cohdl_testutil import cocotb_util


async def add_numbers(inp: Unsigned[32], count: int | Unsigned):
    result = Signal[Unsigned[32]](0)
    counter = Signal[Unsigned.upto(std.max_int(count))](count)

    while True:
        counter <<= counter - 1
        result <<= result + inp

        if counter == 1:
            break

    return result


class test_executor_02(cohdl.Entity):
    clk = Port.input(Bit)
    reset = Port.input(Bit)
    start = Port.input(Bit)

    inp_value = Port.input(Unsigned[32])

    result_parallel = Port.output(Unsigned[32])
    result_before = Port.output(Unsigned[32])
    result_after = Port.output(Unsigned[32])

    is_ready = Port.output(Bit)

    def architecture(self):
        ctx = std.SequentialContext(
            std.Clock(self.clk),
            std.Reset(self.reset),
        )

        exec_parallel = std.Executor.make_parallel(
            ctx,
            add_numbers,
            result=Signal[Unsigned[32]](),
            inp=self.inp_value,
            count=12,
        )

        exec_after = std.Executor.make_after(
            add_numbers, result=Variable[Unsigned[32]](), inp=self.inp_value, count=12
        )

        exec_before = std.Executor.make_before(
            add_numbers, result=Variable[Unsigned[32]](), inp=self.inp_value, count=12
        )

        std.concurrent_eval(self.is_ready, exec_parallel.ready)

        @ctx
        async def proc_parallel():
            await self.start
            exec_parallel.start()
            await exec_parallel.ready()
            self.result_parallel <<= exec_parallel.result()

            await self.start
            self.result_parallel <<= await exec_parallel.exec()

        @ctx
        async def proc_after():
            await self.start
            exec_after.start()
            await exec_after.ready()
            self.result_after <<= exec_after.result()

            await self.start
            self.result_after <<= await exec_after.exec()

        @ctx(executors=[exec_before])
        async def proc_before():
            await self.start
            exec_before.start()
            await exec_before.ready()
            self.result_before <<= exec_before.result()

            await self.start
            self.result_before <<= await exec_before.exec()


if False:
    print(std.VhdlCompiler.to_string(test_executor_02))

else:
    #
    # test code
    #

    def gen_onehot():
        for i in range(30):
            yield 1 << i

    @cocotb_util.test()
    async def testbench_executor_02(dut: test_executor_02):
        gen = cocotb_util.ConstrainedGenerator(32)

        seq = cocotb_util.SequentialTest(dut.clk)
        dut.start.value = False
        dut.reset.value = True
        dut.inp_value.value = 0
        await seq.tick()
        await seq.tick()
        dut.reset.value = False

        for _ in range(4):
            await seq.tick()
            dut.start.value = True

            values = []

            for nr, inp_value in enumerate(gen.random(16)):
                values.append(inp_value)
                dut.inp_value.value = inp_value.as_int()
                await seq.tick()
                dut.start.value = False

                if nr == 11:
                    res_a = sum(values[-11:])
                elif nr == 12:
                    res_b = sum(values[-11:])

                if nr >= 13:
                    assert dut.result_after.value == res_a.as_int()
                    assert dut.result_before.value == res_b.as_int()
                elif nr >= 14:
                    assert dut.result_parallel.value == res_b.as_int()

    class Unittest(unittest.TestCase):
        def test_executor_02(self):
            cocotb_util.run_cocotb_tests(
                test_executor_02,
                __file__,
                self.__module__,
            )
