import unittest

import cohdl
from cohdl import Bit, Port, Unsigned, Variable
from cohdl import std

from cohdl_testutil import cocotb_util


class SimpleContext:
    def __init__(self, output, counter, level_monitor, output_cnt=1):
        self.output = output
        self.counter = counter
        self.level_monitor = level_monitor
        self.output_cnt = output_cnt

    def __enter__(self):
        self.counter @= self.counter + 1
        self.output <<= self.counter
        self.level_monitor <<= self.counter

        if self.output_cnt == 1:
            return self
        else:
            return [self for _ in range(self.output_cnt)]

    def __exit__(self, type, value, traceback):
        self.counter @= self.counter - 1
        self.output <<= self.counter
        self.level_monitor <<= self.counter


class test_context_manager_01(cohdl.Entity):
    clk = Port.input(Bit)
    reset = Port.input(Bit)

    ctx_a = Port.output(Unsigned[4], default=0)
    ctx_b = Port.output(Unsigned[4], default=0)
    ctx_c = Port.output(Unsigned[4], default=0)
    ctx_d = Port.output(Unsigned[4], default=0)

    level = Port.output(Unsigned[4], default=0)

    def architecture(self):
        @std.sequential(std.Clock(self.clk), std.Reset(self.reset))
        async def proc():
            level = Variable[Unsigned[4]](0)

            with SimpleContext(self.ctx_a, level, self.level):
                with SimpleContext(self.ctx_b, level, self.level) as b:
                    await std.wait_for(3)
                    assert b.output is self.ctx_b
                    with SimpleContext(self.ctx_c, level, self.level, output_cnt=2) as (
                        c,
                        cc,
                    ):
                        await std.wait_for(1)
                        assert c.output is self.ctx_c
                        assert cc is c
                        with SimpleContext(
                            self.ctx_d, level, self.level
                        ) as d, SimpleContext(
                            self.ctx_c, level, self.level, output_cnt=3
                        ) as (
                            c1,
                            c2,
                            c3,
                        ):
                            assert d.output is self.ctx_d
                            assert c1 is c2 is c3
                            await std.wait_for(2)
                        await std.wait_for(1)
                    await std.wait_for(2)

            assert level == 0


#
# test code
#


@cocotb_util.test()
async def testbench_context_manager_01(dut: test_context_manager_01):
    seq = cocotb_util.SequentialTest(dut.clk)

    dut.reset.value = True
    await seq.tick()
    dut.reset.value = False

    a = 0
    b = 0
    c = 0
    d = 0
    level = 0

    def expected_generator():
        nonlocal a, b, c, d, level

        while True:
            a = 1
            b = 2
            level = 2
            yield
            yield
            yield
            c = 3
            level = 3
            yield
            d = 4
            c = 5
            level = 5
            yield
            yield
            c = 4
            d = 3
            level = 3
            yield
            c = 2
            level = 2
            yield
            yield
            b = 1
            a = 0
            level = 0
            yield

    for _ in zip(range(64), expected_generator()):
        await seq.tick()
        assert a == dut.ctx_a.value
        assert b == dut.ctx_b.value
        assert c == dut.ctx_c.value
        assert d == dut.ctx_d.value
        assert level == dut.level.value


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_context_manager_01, __file__, self.__module__)
