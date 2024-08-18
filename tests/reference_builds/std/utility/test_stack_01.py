from __future__ import annotations

import unittest
import cohdl
from cohdl import std, Bit, Port, Unsigned

from cohdl_testutil import cocotb_util

drop_old = None


class test_stack_01(cohdl.Entity):
    clk = Port.input(Bit)
    reset = Port.input(Bit)

    data_1 = Port.input(Bit)
    push_1 = Port.input(Bit)
    pop_1 = Port.input(Bit)
    reset_1 = Port.input(Bit)

    out_1 = Port.output(Bit, default=False)
    front_1 = Port.output(Bit, default=False)
    empty_1 = Port.output(Bit, default=True)
    full_1 = Port.output(Bit, default=False)
    size_1 = Port.output(Unsigned[4], default=0)

    def architecture(self):
        ctx = std.SequentialContext(std.Clock(self.clk), std.Reset(self.reset))

        if drop_old is None:
            stack = std.Stack[Bit, 5]()
        elif drop_old:
            stack = std.Stack[Bit, 5](mode=std.StackMode.DROP_OLD)
        else:
            stack = std.Stack[Bit, 5](mode=std.StackMode.NO_OVERFLOW)

        @ctx
        def proc_stack_01():

            if self.push_1:
                stack.push(self.data_1)

            if self.pop_1:
                self.out_1 <<= stack.pop()

            if self.reset_1:
                stack.reset()

            self.empty_1 <<= stack.empty()
            self.full_1 <<= stack.full()
            self.size_1 <<= stack.size()

            if not stack.empty():
                self.front_1 <<= stack.front()
            else:
                self.front_1 <<= False


#
# test code
#


@cocotb_util.test()
async def testbench_stack_01(dut: test_stack_01):
    seq = cocotb_util.SequentialTest(dut.clk)
    dut.reset.value = False
    dut.clk.value = False
    dut.data_1.value = 0
    dut.push_1.value = 0
    dut.pop_1.value = 0
    dut.reset_1.value = 0

    def check(empty, full, out, front, size=None):
        assert dut.empty_1 == empty
        assert dut.full_1 == full
        assert dut.out_1 == out
        assert dut.front_1 == front

        if size is not None:
            assert dut.size_1 == size

    await seq.tick()
    check(True, False, 0, 0, 0)
    dut.reset.value = True

    await seq.tick()
    check(True, False, 0, 0, 0)
    dut.reset.value = False

    await seq.tick()
    check(True, False, 0, 0, 0)
    dut.data_1.value = 1
    dut.push_1.value = 1

    await seq.tick()
    check(True, False, 0, 0, 0)
    dut.push_1.value = 0
    dut.pop_1.value = 1

    await seq.tick()
    check(False, False, 1, 1, 1)
    dut.push_1.value = 0
    dut.pop_1.value = 0

    await seq.tick()
    check(True, False, 1, 0, 0)

    await seq.tick()
    check(True, False, 1, 0, 0)

    #
    #
    #

    await seq.tick()
    check(True, False, 1, 0, 0)
    dut.push_1.value = 1
    dut.data_1.value = 0

    await seq.tick()
    dut.data_1.value = 0
    check(True, False, 1, 0, 0)

    await seq.tick()
    check(False, False, 1, 0, 1)
    dut.data_1.value = 1

    await seq.tick()
    check(False, False, 1, 0, 2)

    await seq.tick()
    check(False, False, 1, 1, 3)

    await seq.tick()
    check(False, False, 1, 1, 4)
    dut.push_1.value = 0

    await seq.tick()
    check(False, True, 1, 1, 5)

    await seq.tick()
    check(False, True, 1, 1, 5)
    dut.pop_1.value = 1

    await seq.tick()
    check(False, True, 1, 1, 5)

    await seq.tick()
    check(False, False, 1, 1, 4)
    dut.pop_1.value = 0
    dut.reset_1.value = 1

    await seq.tick()
    check(False, False, 1, 1, 3)
    dut.reset_1.value = 0

    await seq.tick()
    check(True, False, 1, 0, 0)

    await seq.tick()
    check(True, False, 1, 0, 0)

    await seq.tick()
    check(True, False, 1, 0, 0)


class Unittest(unittest.TestCase):
    def test_stack_01_default(self):
        global drop_old
        drop_old = None
        cocotb_util.run_cocotb_tests(test_stack_01, __file__, self.__module__)

    def test_stack_01_no_overflow(self):
        global drop_old
        drop_old = False
        cocotb_util.run_cocotb_tests(test_stack_01, __file__, self.__module__)

    def test_stack_01_drop_old(self):
        global drop_old
        drop_old = True
        cocotb_util.run_cocotb_tests(test_stack_01, __file__, self.__module__)
