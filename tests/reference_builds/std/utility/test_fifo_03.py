from __future__ import annotations

import unittest

import cohdl
from cohdl import std, Bit, Port

from cohdl_testutil import cocotb_util

import os

rx_delay: int = eval(os.getenv("cohdl_test_rx_delay", "None"))
tx_delay: int = eval(os.getenv("cohdl_test_tx_delay", "None"))


def gen_entity():
    class test_fifo_03(cohdl.Entity):
        clk = Port.input(Bit)
        reset = Port.input(Bit)

        start_sender = Port.input(Bit)

        set_flag = Port.output(Bit, default=False)
        clear_flag = Port.output(Bit, default=False)

        is_set = Port.output(Bit)
        is_clear = Port.output(Bit)

        is_set_in_sender = Port.output(Bit)
        is_clear_in_sender = Port.output(Bit)

        is_set_in_receiver = Port.output(Bit)
        is_clear_in_receiver = Port.output(Bit)

        def architecture(self):
            ctx = std.SequentialContext(std.Clock(self.clk), std.Reset(self.reset))
            sync = std.SyncFlag(rx_delay=rx_delay, tx_delay=tx_delay)

            @std.concurrent
            def logic():
                self.is_set <<= sync.is_set()
                self.is_clear <<= sync.is_clear()

            @ctx
            async def set_sync():
                if self.start_sender:
                    sync.set()
                    self.set_flag ^= True

                self.is_set_in_sender <<= sync.is_set()
                self.is_clear_in_sender <<= sync.is_clear()

            @ctx
            async def clear_sync():
                if sync.is_set():
                    sync.clear()
                    self.clear_flag ^= True

                self.is_set_in_receiver <<= sync.is_set()
                self.is_clear_in_receiver <<= sync.is_clear()

    return test_fifo_03


#
# test code
#


@cocotb_util.test()
async def testbench_fifo_03_mock(dut: test_fifo_03):
    dut.reset.value = 0
    dut.clk.value = 0
    dut.start_sender.value = 0

    seq = cocotb_util.SequentialTest(dut.clk)
    await seq.tick()

    sender_cnt = None

    for nr in range(64):
        if nr % 16 == 8:
            dut.start_sender.value = 1
            sender_cnt = 0
        else:
            dut.start_sender.value = 0

        if sender_cnt is not None:
            assert dut.is_set == (1 + tx_delay <= sender_cnt <= 1 + tx_delay + rx_delay)
            assert dut.is_clear == (
                not (1 + tx_delay <= sender_cnt <= 1 + tx_delay + rx_delay)
            )

            assert dut.is_set_in_sender == (2 <= sender_cnt <= 2 + tx_delay + rx_delay)
            assert dut.is_clear_in_sender == (
                not (2 <= sender_cnt <= 2 + tx_delay + rx_delay)
            )

            assert dut.is_set_in_receiver == (sender_cnt == 2 + tx_delay)
            assert dut.is_clear_in_receiver == (sender_cnt != 2 + tx_delay)

            sender_cnt += 1

        await seq.tick()


class Unittest(unittest.TestCase):
    def _test_with_args(self, rx_delay_val, tx_delay_val):
        global rx_delay, tx_delay

        rx_delay = rx_delay_val
        tx_delay = tx_delay_val

        cocotb_util.run_cocotb_tests(
            gen_entity(),
            __file__,
            self.__module__,
            extra_env={
                "cohdl_test_rx_delay": f"{rx_delay_val}",
                "cohdl_test_tx_delay": f"{tx_delay_val}",
            },
        )

    def test_fifo_03_0_0(self):
        self._test_with_args(0, 0)

    def test_fifo_03_0_1(self):
        self._test_with_args(0, 1)

    def test_fifo_03_1_0(self):
        self._test_with_args(1, 0)

    def test_fifo_03_0_2(self):
        self._test_with_args(0, 2)

    def test_fifo_03_2_0(self):
        self._test_with_args(2, 0)

    def test_fifo_03_1_3(self):
        self._test_with_args(0, 3)

    def test_fifo_03_4_2(self):
        self._test_with_args(4, 2)
