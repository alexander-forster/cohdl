from __future__ import annotations

import unittest

import cohdl
from cohdl import std, Bit, Port, BitVector, Signed

from cohdl_testutil import cocotb_util
import cocotb


class MyRecord(std.Record):
    a: Bit
    b: BitVector[7]
    c: Signed[8]
    d: std.Array[Bit, 8]
    e: std.Array[std.Array[BitVector[1], 4], 2]


class test_fifo_03(cohdl.Entity):
    clk = Port.input(Bit)
    reset = Port.input(Bit)
    receive = Port.input(Bit)

    in_bit = Port.input(Bit)
    in_bit_vector = Port.input(BitVector[7])
    in_signed = Port.input(Signed[8])
    in_array = Port.input(BitVector[8])
    in_array2 = Port.input(BitVector[8])
    in_valid = Port.input(Bit)

    out_bit = Port.output(Bit)
    out_bit_vector = Port.output(BitVector[7])
    out_signed = Port.output(Signed[8])
    out_array = Port.output(BitVector[8])
    out_array2 = Port.output(BitVector[8])

    out_rec_bit = Port.output(Bit)
    out_rec_bit_vector = Port.output(BitVector[7])
    out_rec_signed = Port.output(Signed[8])
    out_rec_array = Port.output(BitVector[8])
    out_rec_array2 = Port.output(BitVector[8])

    is_full_and = Port.output(Bit)
    is_empty_and = Port.output(Bit)

    is_full_or = Port.output(Bit)
    is_empty_or = Port.output(Bit)

    def architecture(self):
        clk = std.Clock(self.clk)
        reset = std.Reset(self.reset)

        ctx = std.SequentialContext(
            clk, reset, attributes={"zero_init_temporaries": True}
        )
        ctx_receive = ctx.with_params(step_cond=lambda: self.receive)

        fifo_bit = std.Fifo[Bit, 4]()
        fifo_bit_vector = std.Fifo[BitVector[7], 4]()
        fifo_signed = std.Fifo[Signed[8], 4]()
        fifo_array = std.Fifo[std.Array[Bit, 8], 4]()
        fifo_array2 = std.Fifo[std.Array[std.Array[BitVector[1], 4], 2], 4]()
        fifo_record = std.Fifo[MyRecord, 4]()

        fifos: list[std.Fifo] = [
            fifo_bit,
            fifo_bit_vector,
            fifo_signed,
            fifo_array,
            fifo_array2,
            fifo_record,
        ]

        in_array = std.Array[Bit, 8]()
        in_array2 = std.Array[std.Array[BitVector[1], 4], 2]()

        @std.concurrent(attributes={"zero_init_temporaries": True})
        def logic():
            self.is_full_and <<= all([fifo.full() for fifo in fifos])
            self.is_full_or <<= any([fifo.full() for fifo in fifos])

            self.is_empty_and <<= all([fifo.empty() for fifo in fifos])
            self.is_empty_or <<= any([fifo.empty() for fifo in fifos])

            for inp, local in zip(self.in_array, in_array):
                local <<= inp

            for outer in (0, 1):
                for inner in (0, 1, 2, 3):
                    idx = outer * 4 + inner
                    in_array2[outer][inner] <<= self.in_array2[idx:idx]

        @ctx
        async def proc_sender():
            await self.in_valid

            fifo_bit.push(self.in_bit)
            fifo_bit_vector.push(self.in_bit_vector)
            fifo_signed.push(self.in_signed)
            fifo_array.push(in_array)
            fifo_array2.push(in_array2)

            fifo_record.push(
                MyRecord(
                    a=self.in_bit,
                    b=self.in_bit_vector,
                    c=self.in_signed,
                    d=in_array,
                    e=in_array2,
                )
            )

        @ctx_receive
        async def proc_receiver_bit():
            self.out_bit <<= await fifo_bit.receive()

        @ctx_receive
        async def proc_receiver_bit_vector():
            self.out_bit_vector <<= await fifo_bit_vector.receive()

        @ctx_receive
        async def proc_receiver_signed():
            self.out_signed <<= await fifo_signed.receive()

        @ctx_receive
        async def proc_receiver_array():
            data = await fifo_array.receive()

            for out_bit, data_bit in zip(self.out_array, data):
                out_bit <<= data_bit

        @ctx_receive
        async def proc_receiver_array2():
            data = await fifo_array2.receive()

            for outer in (0, 1):
                for inner in (0, 1, 2, 3):
                    idx = outer * 4 + inner
                    self.out_array2[idx:idx] <<= data[outer][inner]

        @ctx_receive
        async def proc_receiver_record():
            data = await fifo_record.receive(qualifier=std.Value)

            self.out_rec_bit <<= data.a
            self.out_rec_bit_vector <<= data.b
            self.out_rec_signed <<= data.c

            for out_bit, data_bit in zip(self.out_rec_array, data.d):
                out_bit <<= data_bit

            for outer in (0, 1):
                for inner in (0, 1, 2, 3):
                    idx = outer * 4 + inner
                    self.out_rec_array2[idx:idx] <<= data.e[outer][inner]


#
# test code
#


async def check_consistent_empty_full(dut: test_fifo_03):
    while True:
        await cocotb_util.RisingEdge(dut.clk)
        assert dut.is_full_and.value == dut.is_full_or.value
        assert dut.is_empty_and.value == dut.is_empty_or.value


class InputSet:
    def __init__(self):
        gen = cocotb_util.ConstrainedGenerator

        self.bit = gen(1).random()
        self.bit_vector = gen(7).random()
        self.signed = gen(8).random()
        self.array = gen(8).random()
        self.array2 = gen(8).random()

    def apply(self, dut: test_fifo_03):
        dut.in_bit.value = self.bit.as_int()
        dut.in_bit_vector.value = self.bit_vector.as_int()
        dut.in_signed.value = self.signed.as_int()
        dut.in_array.value = self.array.as_int()
        dut.in_array2.value = self.array2.as_int()

    def check(self, dut: test_fifo_03):
        assert dut.out_bit.value == self.bit.as_int()
        assert dut.out_bit_vector.value == self.bit_vector.as_int()
        assert dut.out_signed.value == self.signed.as_int()
        assert dut.out_array.value == self.array.as_int()
        assert dut.out_array2.value == self.array2.as_int()

        assert dut.out_rec_bit.value == self.bit.as_int()
        assert dut.out_rec_bit_vector.value == self.bit_vector.as_int()
        assert dut.out_rec_signed.value == self.signed.as_int()
        assert dut.out_rec_array.value == self.array.as_int()
        assert dut.out_rec_array2.value == self.array2.as_int()


@cocotb_util.test()
async def testbench_fifo_03(dut: test_fifo_03):

    dut.receive.value = 0
    dut.reset.value = 1
    dut.clk.value = 0

    seq = cocotb_util.SequentialTest(dut.clk)

    await seq.tick()
    await seq.tick()

    dut.reset.value = 0

    cocotb.start_soon(check_consistent_empty_full(dut))

    for _ in range(10):
        await seq.tick()
        assert dut.is_empty_and.value == True
        assert dut.is_full_and.value == False

    inp: list[InputSet] = []

    for nr in range(3):
        new = InputSet()
        inp.append(new)
        new.apply(dut)
        dut.in_valid.value = True
        await seq.tick()
        dut.in_valid.value = False

        assert dut.is_empty_and.value == False
        assert dut.is_full_and.value == (nr == 2)

    dut.receive.value = True

    while len(inp) != 0:
        await seq.tick()
        inp[0].check(dut)
        del inp[0]

        assert dut.is_empty_and.value == (len(inp) == 0)
        assert dut.is_full_and.value == False

    new = InputSet()
    inp.append(new)
    new.apply(dut)
    dut.in_valid.value = True
    await seq.tick()
    dut.in_valid.value = False

    for nr in range(5):
        new = InputSet()
        inp.append(new)
        new.apply(dut)
        dut.in_valid.value = True
        await seq.tick()
        dut.in_valid.value = False

        inp[0].check(dut)
        del inp[0]

        assert dut.is_empty_and.value == False
        assert dut.is_full_and.value == False

    assert len(inp) == 1
    await seq.tick()
    inp[0].check(dut)
    del inp[0]

    assert dut.is_empty_and.value == True
    assert dut.is_full_and.value == False


class Unittest(unittest.TestCase):
    def test_fifo(self):
        cocotb_util.run_cocotb_tests(test_fifo_03, __file__, self.__module__)
