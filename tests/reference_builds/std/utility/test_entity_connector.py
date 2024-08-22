from __future__ import annotations

import unittest

import cohdl
from cohdl import std, Bit, BitVector, Unsigned, Port, Signal, Null

from cohdl_testutil import cocotb_util


class InnerEntity(cohdl.Entity):
    inp_bit = Port.input(Bit)
    out_bit = Port.output(Bit)

    def architecture(self):

        @std.concurrent
        def logic():
            self.out_bit <<= ~self.inp_bit


class OuterEntity(cohdl.Entity):
    inp_a = Port.input(Bit)
    out_a = Port.output(Bit)

    inp_b = Port.input(BitVector[7])
    out_b = Port.output(BitVector[7])

    inp_c = Port.input(BitVector[7])
    out_c = Port.output(BitVector[7])

    inp_d = Port.input(BitVector[7])
    out_d = Port.output(BitVector[7])

    inp_e = Port.input(BitVector[7])
    out_e = Port.output(BitVector[7])

    def architecture(self):

        InnerEntity(inp_bit=self.inp_a, out_bit=self.out_a)

        @std.concurrent
        def logic():
            out_b0 = Signal[Bit]()
            InnerEntity(inp_bit=self.inp_b[0], out_bit=out_b0)
            self.out_b[0] <<= out_b0

            con_in = Signal[Bit]()
            con_out = Signal[Bit]()
            InnerEntity(inp_bit=con_in, out_bit=con_out)
            con_in <<= self.inp_b[1]
            self.out_b[1] <<= con_out

            open_ent = std.OpenEntity[InnerEntity](inp_bit=self.inp_b[2])
            self.out_b[2] <<= open_ent.out_bit

            connected_ent = std.ConnectedEntity[InnerEntity]()
            connected_ent.inp_bit <<= self.inp_b[3]
            self.out_b[3] <<= connected_ent.out_bit

            #

            out_b4 = Signal[Bit]()
            std.OpenEntity[InnerEntity](inp_bit=self.inp_b[4], out_bit=out_b4)
            self.out_b[4] <<= out_b4

            connected_ent_2 = std.ConnectedEntity[InnerEntity](inp_bit=self.inp_b[5])
            self.out_b[5] <<= connected_ent_2.out_bit

            out_b6 = Signal[Bit]()
            connected_ent_3 = std.ConnectedEntity[InnerEntity](out_bit=out_b6)
            connected_ent_3.inp_bit <<= self.inp_b[6]
            self.out_b[6] <<= out_b6

        @std.sequential
        def logic():
            with cohdl.always:
                out_c0 = Signal[Bit]()
                InnerEntity(inp_bit=self.inp_c[0], out_bit=out_c0)
                self.out_c[0] <<= out_c0

                con_in = Signal[Bit]()
                con_out = Signal[Bit]()
                InnerEntity(inp_bit=con_in, out_bit=con_out)
                con_in <<= self.inp_c[1]
                self.out_c[1] <<= con_out

                open_ent = std.OpenEntity[InnerEntity](inp_bit=self.inp_c[2])
                self.out_c[2] <<= open_ent.out_bit

                connected_ent = std.ConnectedEntity[InnerEntity]()
                connected_ent.inp_bit <<= self.inp_c[3]
                self.out_c[3] <<= connected_ent.out_bit

                #

                out_c4 = Signal[Bit]()
                std.OpenEntity[InnerEntity](inp_bit=self.inp_c[4], out_bit=out_c4)
                self.out_c[4] <<= out_c4

                connected_ent_2 = std.ConnectedEntity[InnerEntity](
                    inp_bit=self.inp_c[5]
                )
                self.out_c[5] <<= connected_ent_2.out_bit

                out_c6 = Signal[Bit]()
                connected_ent_3 = std.ConnectedEntity[InnerEntity](out_bit=out_c6)
                connected_ent_3.inp_bit <<= self.inp_c[6]
                self.out_c[6] <<= out_c6

        @std.sequential
        def logic():
            always = cohdl.always

            out_d0 = Signal[Bit]()
            always(InnerEntity(inp_bit=self.inp_d[0], out_bit=out_d0))
            self.out_d[0] <<= out_d0

            con_in = Signal[Bit]()
            con_out = Signal[Bit]()
            always(InnerEntity(inp_bit=con_in, out_bit=con_out))
            con_in <<= self.inp_d[1]
            self.out_d[1] <<= con_out

            open_ent = always(std.OpenEntity[InnerEntity](inp_bit=self.inp_d[2]))
            self.out_d[2] <<= open_ent.out_bit

            connected_ent = always(std.ConnectedEntity[InnerEntity]())
            connected_ent.inp_bit <<= self.inp_d[3]
            self.out_d[3] <<= connected_ent.out_bit

            #

            out_d4 = Signal[Bit]()
            always(std.OpenEntity[InnerEntity](inp_bit=self.inp_d[4], out_bit=out_d4))
            self.out_d[4] <<= out_d4

            connected_ent_2 = always(
                std.ConnectedEntity[InnerEntity](inp_bit=self.inp_d[5])
            )
            self.out_d[5] <<= connected_ent_2.out_bit

            out_d6 = Signal[Bit]()
            connected_ent_3 = always(std.ConnectedEntity[InnerEntity](out_bit=out_d6))
            connected_ent_3.inp_bit <<= self.inp_d[6]
            self.out_d[6] <<= out_d6

        #

        out_e0 = Signal[Bit]()
        out_e4 = Signal[Bit]()
        out_e6 = Signal[Bit]()

        InnerEntity(inp_bit=self.inp_e[0], out_bit=out_e0)

        con_in_e = Signal[Bit]()
        con_out_e = Signal[Bit]()
        InnerEntity(inp_bit=con_in_e, out_bit=con_out_e)
        open_ent_e = std.OpenEntity[InnerEntity](inp_bit=self.inp_e[2])
        connected_ent_e = std.ConnectedEntity[InnerEntity]()
        std.OpenEntity[InnerEntity](inp_bit=self.inp_e[4], out_bit=out_e4)

        connected_ent_e2 = std.ConnectedEntity[InnerEntity](inp_bit=self.inp_e[5])
        connected_ent_e3 = std.ConnectedEntity[InnerEntity](out_bit=out_e6)

        @std.concurrent
        def logic():
            self.out_e[0] <<= out_e0

            con_in_e.next = self.inp_e[1]
            self.out_e[1] <<= con_out_e

            self.out_e[2] <<= open_ent_e.out_bit

            connected_ent_e.inp_bit <<= self.inp_e[3]
            self.out_e[3] <<= connected_ent_e.out_bit

            self.out_e[4] <<= out_e4

            #

            self.out_e[5] <<= connected_ent_e2.out_bit

            connected_ent_e3.inp_bit <<= self.inp_e[6]
            self.out_e[6] <<= out_e6


class test_entity_connector(cohdl.Entity):
    inp_a = Port.input(Bit)
    out_a = Port.output(Bit)

    inp_b = Port.input(BitVector[7])
    out_b = Port.output(BitVector[7])

    inp_c = Port.input(BitVector[7])
    out_c = Port.output(BitVector[7])

    inp_d = Port.input(BitVector[7])
    out_d = Port.output(BitVector[7])

    inp_e = Port.input(BitVector[7])
    out_e = Port.output(BitVector[7])

    def architecture(self):

        OuterEntity(
            inp_a=self.inp_a,
            out_a=self.out_a,
            inp_b=self.inp_b,
            out_b=self.out_b,
            inp_c=self.inp_c,
            out_c=self.out_c,
            inp_d=self.inp_d,
            out_d=self.out_d,
            inp_e=self.inp_e,
            out_e=self.out_e,
        )


#
# test code
#


@cocotb_util.test()
async def testbench_entity_connector(dut: test_entity_connector):
    gen_bit = cocotb_util.ConstrainedGenerator(1)
    gen_vec = cocotb_util.ConstrainedGenerator(7)

    for _ in range(256):
        a = gen_bit.random()
        b, c, d, e = gen_vec.random(4)

        dut.inp_a.value = a.as_int()
        dut.inp_b.value = b.as_int()
        dut.inp_c.value = c.as_int()
        dut.inp_d.value = d.as_int()
        dut.inp_e.value = e.as_int()

        await cocotb_util.step()

        assert dut.out_a == ~a
        assert dut.out_b == ~b
        assert dut.out_c == ~c
        assert dut.out_d == ~d
        assert dut.out_e == ~e


class Unittest(unittest.TestCase):
    def test_hdl(self):
        cocotb_util.run_cocotb_tests(test_entity_connector, __file__, self.__module__)
