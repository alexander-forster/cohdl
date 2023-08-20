from __future__ import annotations

import unittest

import cohdl
from cohdl import std, Bit, Port, expr

from cohdl_testutil import cocotb_util


class test_sync_flag_02(cohdl.Entity):
    clk = Port.input(Bit)
    reset = Port.input(Bit)

    start_sender = Port.input(Bit)
    start_receiver = Port.input(Bit)

    received_flag = Port.output(Bit, default=False)
    received_clear = Port.output(Bit, default=False)

    is_set = Port.output(Bit)
    is_clear = Port.output(Bit)

    def architecture(self):
        ctx = std.SequentialContext(std.Clock(self.clk), std.Reset(self.reset))

        sync = std.SyncFlag()

        @std.concurrent
        def logic():
            self.is_set <<= sync.is_set()
            self.is_clear <<= sync.is_clear()

        @ctx
        async def set_sync():
            await self.start_sender
            sync.set()
            await sync.is_clear()
            self.received_clear ^= True

        @ctx
        async def clear_sync():
            await self.start_receiver
            async with sync:
                self.received_flag ^= True
                await expr(not self.start_receiver)


#
# test code
#


class SyncMock:
    def _sender(self):
        while True:
            while not self.start_sender:
                yield
            self._next_flag = True

            yield
            while self._flag:
                yield
            self.received_clear = True
            yield

    def _receiver(self):
        while True:
            while not self.start_receiver:
                yield
            yield
            while not self._flag:
                yield
            self.received_flag = True

            yield
            while self.start_receiver:
                yield
            self._next_flag = False
            yield

    def __init__(self):
        self.start_sender = False
        self.start_receiver = False

        self.received_flag = False
        self.received_clear = False

        self._flag = False
        self._next_flag = False

        self._run_sender = self._sender()
        self._run_receiver = self._receiver()

    def step(self):
        next(self._run_sender)
        next(self._run_receiver)
        self._flag = self._next_flag

    def is_set(self):
        return self._flag

    def is_clear(self):
        return not self._flag


class SyncTester:
    async def step(self):
        await self.seq.tick()

    def __init__(self, dut: test_sync_flag_02):
        self.dut = dut
        self.seq = cocotb_util.SequentialTest(dut.clk)
        self.mock = SyncMock()

    async def reset(self):
        self.dut.clk.value = 0
        self.dut.reset.value = True
        self.dut.start_sender.value = False
        self.dut.start_receiver.value = False
        await self.seq.tick()
        self.dut.reset.value = False
        await self.seq.tick()

    async def step(self):
        await self.seq.tick()
        self.mock.step()
        self.set_start_sender(False)

        assert self.dut.is_set.value == self.mock.is_set()
        assert self.dut.is_clear.value == self.mock.is_clear()
        assert self.dut.received_flag.value == self.mock.received_flag
        assert self.dut.received_clear.value == self.mock.received_clear
        self.mock.received_flag = False
        self.mock.received_clear = False

    def set_start_sender(self, val):
        self.dut.start_sender.value = val
        self.mock.start_sender = val

    def set_start_receiver(self, val):
        self.dut.start_receiver.value = val
        self.mock.start_receiver = val

    def is_set(self):
        assert self.dut.is_set.value == self.mock.is_set()
        return self.mock.is_set()

    def is_clear(self):
        assert self.dut.is_clear.value == self.mock.is_clear()
        return self.mock.is_clear()


@cocotb_util.test()
async def testbench_sync_flag_02_mock(dut: test_sync_flag_02):
    tester = SyncTester(dut)
    await tester.reset()

    for _ in range(4):
        tester.set_start_sender(True)
        tester.set_start_receiver(True)

        await tester.step()
        await tester.step()
        await tester.step()
        await tester.step()
        await tester.step()

        tester.set_start_receiver(False)
        await tester.step()
        await tester.step()
        await tester.step()


@cocotb_util.test()
async def testbench_sync_flag_02_mock_delay(dut: test_sync_flag_02):
    tester = SyncTester(dut)
    await tester.reset()

    for sender_delay_val in (0, 1, 2, 3):
        for receiver_delay_val in (0, 1, 2, 3):
            for clear_delay_val in (1, 2, 5):
                sender_delay = sender_delay_val
                receiver_delay = receiver_delay_val
                clear_delay = clear_delay_val + receiver_delay_val
                for _ in range(15):
                    if sender_delay == 0:
                        tester.set_start_sender(True)
                    if receiver_delay == 0:
                        tester.set_start_receiver(True)
                    if clear_delay == 0:
                        tester.set_start_receiver(False)

                    sender_delay -= 1
                    receiver_delay -= 1
                    clear_delay -= 1

                    await tester.step()


class Unittest(unittest.TestCase):
    def test_sync_flag_02(self):
        cocotb_util.run_cocotb_tests(test_sync_flag_02, __file__, self.__module__)
