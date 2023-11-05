from __future__ import annotations

import unittest

import cohdl
from cohdl import std, Bit, Port, BitVector, Unsigned, Signal

from cohdl_testutil import cocotb_util


class test_mailbox_02(cohdl.Entity):
    clk = Port.input(Bit)

    mailbox_data = Port.output(BitVector[8])
    received_data = Port.output(BitVector[8])

    is_set = Port.output(Bit)
    is_clear = Port.output(Bit)

    def architecture(self):
        ctx = std.SequentialContext(std.Clock(self.clk))

        mailbox = std.Mailbox(BitVector[8])

        @std.concurrent
        def logic():
            self.mailbox_data <<= mailbox.data()
            self.is_set <<= mailbox.is_set()
            self.is_clear <<= mailbox.is_clear()

        @ctx
        async def proc_sender(counter=Signal[Unsigned[8]](0)):
            # this test is also used to check the while-continue pattern
            while True:
                mailbox.send(counter)
                counter <<= counter + 1
                await mailbox.is_clear()
                continue

        @ctx
        async def proc_receiver():
            self.received_data <<= await mailbox.receive()


#
# test code
#


@cocotb_util.test()
async def testbench_mailbox_02(dut: test_mailbox_02):
    seq = cocotb_util.SequentialTest(dut.clk)
    await seq.tick()

    for cnt in range(40):
        assert dut.is_clear.value == True
        assert dut.is_set.value == False

        if cnt != 0:
            assert dut.received_data.value == cnt - 1

        await seq.tick()
        assert dut.is_clear.value == False
        assert dut.is_set.value == True
        assert dut.mailbox_data.value == cnt
        await seq.tick()


class Unittest(unittest.TestCase):
    def test_mailbox_02(self):
        cocotb_util.run_cocotb_tests(test_mailbox_02, __file__, self.__module__)
