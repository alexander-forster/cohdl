from __future__ import annotations

import unittest

import cohdl
from cohdl import Bit, BitVector, Port, Signal, Variable, Unsigned, Signed, Null, Full

from cohdl_testutil import cocotb_util
from cohdl import std


class TestRecord(std.Record):
    a: Bit
    b: Bit
    c: BitVector[4]
    d: Unsigned[5]
    e: Signed[3]
    f: bool
    g: int


class test_reset_03(cohdl.Entity):
    reset = Port.input(Bit)
    set = Port.input(Bit)

    port_res_a = Port.output(Bit, default=Null)
    port_res_b = Port.output(Bit, default=Full)
    port_res_c = Port.output(BitVector[4], default="1100")
    port_res_d = Port.output(Unsigned[5], default=23)
    port_res_e = Port.output(Signed[3], default=-3)
    port_res_f = Port.output(bool, default=True)
    port_res_g = Port.output(int, default=1235)

    port_no_a = Port.output(Bit, default=Null, noreset=True)
    port_no_b = Port.output(Bit, default=Full, noreset=True)
    port_no_c = Port.output(BitVector[4], default="1100", noreset=True)
    port_no_d = Port.output(Unsigned[5], default=23, noreset=True)
    port_no_e = Port.output(Signed[3], default=-3, noreset=True)
    port_no_f = Port.output(bool, default=True, noreset=True)
    port_no_g = Port.output(int, default=1235, noreset=True)

    sig_res_a = Port.output(Bit)
    sig_res_b = Port.output(Bit)
    sig_res_c = Port.output(BitVector[4])
    sig_res_d = Port.output(Unsigned[5])
    sig_res_e = Port.output(Signed[3])
    sig_res_f = Port.output(bool)
    sig_res_g = Port.output(int)

    sig_no_a = Port.output(Bit)
    sig_no_b = Port.output(Bit)
    sig_no_c = Port.output(BitVector[4])
    sig_no_d = Port.output(Unsigned[5])
    sig_no_e = Port.output(Signed[3])
    sig_no_f = Port.output(bool)
    sig_no_g = Port.output(int)

    var_res_a = Port.output(Bit)
    var_res_b = Port.output(Bit)
    var_res_c = Port.output(BitVector[4])
    var_res_d = Port.output(Unsigned[5])
    var_res_e = Port.output(Signed[3])
    var_res_f = Port.output(bool)
    var_res_g = Port.output(int)

    var_no_a = Port.output(Bit)
    var_no_b = Port.output(Bit)
    var_no_c = Port.output(BitVector[4])
    var_no_d = Port.output(Unsigned[5])
    var_no_e = Port.output(Signed[3])
    var_no_f = Port.output(bool)
    var_no_g = Port.output(int)

    srec_res_a = Port.output(Bit)
    srec_res_b = Port.output(Bit)
    srec_res_c = Port.output(BitVector[4])
    srec_res_d = Port.output(Unsigned[5])
    srec_res_e = Port.output(Signed[3])
    srec_res_f = Port.output(bool)
    srec_res_g = Port.output(int)
    srec_no_a = Port.output(Bit)
    srec_no_b = Port.output(Bit)
    srec_no_c = Port.output(BitVector[4])
    srec_no_d = Port.output(Unsigned[5])
    srec_no_e = Port.output(Signed[3])
    srec_no_f = Port.output(bool)
    srec_no_g = Port.output(int)

    vrec_res_a = Port.output(Bit)
    vrec_res_b = Port.output(Bit)
    vrec_res_c = Port.output(BitVector[4])
    vrec_res_d = Port.output(Unsigned[5])
    vrec_res_e = Port.output(Signed[3])
    vrec_res_f = Port.output(bool)
    vrec_res_g = Port.output(int)
    vrec_no_a = Port.output(Bit)
    vrec_no_b = Port.output(Bit)
    vrec_no_c = Port.output(BitVector[4])
    vrec_no_d = Port.output(Unsigned[5])
    vrec_no_e = Port.output(Signed[3])
    vrec_no_f = Port.output(bool)
    vrec_no_g = Port.output(int)

    def architecture(self):
        srec_res = std.Signal[TestRecord](
            a=Null, b=Full, c="1100", d=23, e=-3, f=True, g=1235
        )
        srec_no = std.NoresetSignal[TestRecord](
            a=Null, b=Full, c="1100", d=23, e=-3, f=True, g=1235
        )

        vrec_res = std.Variable[TestRecord](
            a=Null, b=Full, c="1100", d=23, e=-3, f=True, g=1235
        )
        vrec_no = std.NoresetVariable[TestRecord](
            a=Null, b=Full, c="1100", d=23, e=-3, f=True, g=1235
        )

        s_res_a = Signal[Bit](Null)
        s_res_b = Signal[Bit](Full)
        s_res_c = Signal[BitVector[4]]("1100")
        s_res_d = Signal[Unsigned[5]](23)
        s_res_e = Signal[Signed[3]](-3)
        s_res_f = Signal[bool](True)
        s_res_g = Signal[int](1235)
        s_no_a = Signal[Bit](Null, noreset=True)
        s_no_b = Signal[Bit](Full, noreset=True)
        s_no_c = Signal[BitVector[4]]("1100", noreset=True)
        s_no_d = Signal[Unsigned[5]](23, noreset=True)
        s_no_e = Signal[Signed[3]](-3, noreset=True)
        s_no_f = Signal[bool](True, noreset=True)
        s_no_g = Signal[int](1235, noreset=True)
        v_res_a = Variable[Bit](Null)
        v_res_b = Variable[Bit](Full)
        v_res_c = Variable[BitVector[4]]("1100")
        v_res_d = Variable[Unsigned[5]](23)
        v_res_e = Variable[Signed[3]](-3)
        v_res_f = Variable[bool](True)
        v_res_g = Variable[int](1235)
        v_no_a = Variable[Bit](Null, noreset=True)
        v_no_b = Variable[Bit](Full, noreset=True)
        v_no_c = Variable[BitVector[4]]("1100", noreset=True)
        v_no_d = Variable[Unsigned[5]](23, noreset=True)
        v_no_e = Variable[Signed[3]](-3, noreset=True)
        v_no_f = Variable[bool](True, noreset=True)
        v_no_g = Variable[int](1235, noreset=True)

        @cohdl.sequential_context
        def proc():
            self.sig_res_a <<= s_res_a
            self.sig_res_b <<= s_res_b
            self.sig_res_c <<= s_res_c
            self.sig_res_d <<= s_res_d
            self.sig_res_e <<= s_res_e
            self.sig_res_f <<= s_res_f
            self.sig_res_g <<= s_res_g
            self.sig_no_a <<= s_no_a
            self.sig_no_b <<= s_no_b
            self.sig_no_c <<= s_no_c
            self.sig_no_d <<= s_no_d
            self.sig_no_e <<= s_no_e
            self.sig_no_f <<= s_no_f
            self.sig_no_g <<= s_no_g
            self.var_res_a <<= v_res_a
            self.var_res_b <<= v_res_b
            self.var_res_c <<= v_res_c
            self.var_res_d <<= v_res_d
            self.var_res_e <<= v_res_e
            self.var_res_f <<= v_res_f
            self.var_res_g <<= v_res_g
            self.var_no_a <<= v_no_a
            self.var_no_b <<= v_no_b
            self.var_no_c <<= v_no_c
            self.var_no_d <<= v_no_d
            self.var_no_e <<= v_no_e
            self.var_no_f <<= v_no_f
            self.var_no_g <<= v_no_g

            self.srec_res_a <<= srec_res.a
            self.srec_res_b <<= srec_res.b
            self.srec_res_c <<= srec_res.c
            self.srec_res_d <<= srec_res.d
            self.srec_res_e <<= srec_res.e
            self.srec_res_f <<= srec_res.f
            self.srec_res_g <<= srec_res.g
            self.srec_no_a <<= srec_no.a
            self.srec_no_b <<= srec_no.b
            self.srec_no_c <<= srec_no.c
            self.srec_no_d <<= srec_no.d
            self.srec_no_e <<= srec_no.e
            self.srec_no_f <<= srec_no.f
            self.srec_no_g <<= srec_no.g

            self.vrec_res_a <<= vrec_res.a
            self.vrec_res_b <<= vrec_res.b
            self.vrec_res_c <<= vrec_res.c
            self.vrec_res_d <<= vrec_res.d
            self.vrec_res_e <<= vrec_res.e
            self.vrec_res_f <<= vrec_res.f
            self.vrec_res_g <<= vrec_res.g
            self.vrec_no_a <<= vrec_no.a
            self.vrec_no_b <<= vrec_no.b
            self.vrec_no_c <<= vrec_no.c
            self.vrec_no_d <<= vrec_no.d
            self.vrec_no_e <<= vrec_no.e
            self.vrec_no_f <<= vrec_no.f
            self.vrec_no_g <<= vrec_no.g

            if self.reset:
                cohdl.reset_context()
            elif self.set:
                self.port_res_a <<= True
                self.port_res_b <<= False
                self.port_res_c <<= "0011"
                self.port_res_d <<= 7
                self.port_res_e <<= 0
                self.port_res_f <<= False
                self.port_res_g <<= 87654
                self.port_no_a <<= True
                self.port_no_b <<= False
                self.port_no_c <<= "0011"
                self.port_no_d <<= 7
                self.port_no_e <<= 0
                self.port_no_f <<= False
                self.port_no_g <<= 87654
                s_res_a.next = True
                s_res_b.next = False
                s_res_c.next = "0011"
                s_res_d.next = 7
                s_res_e.next = 0
                s_res_f.next = False
                s_res_g.next = 87654
                s_no_a.next = True
                s_no_b.next = False
                s_no_c.next = "0011"
                s_no_d.next = 7
                s_no_e.next = 0
                s_no_f.next = False
                s_no_g.next = 87654
                v_res_a.value = True
                v_res_b.value = False
                v_res_c.value = "0011"
                v_res_d.value = 7
                v_res_e.value = 0
                v_res_f.value = False
                v_res_g.value = 87654
                v_no_a.value = True
                v_no_b.value = False
                v_no_c.value = "0011"
                v_no_d.value = 7
                v_no_e.value = 0
                v_no_f.value = False
                v_no_g.value = 87654

                srec_res.a.next = True
                srec_res.b.next = False
                srec_res.c.next = "0011"
                srec_res.d.next = 7
                srec_res.e.next = 0
                srec_res.f.next = False
                srec_res.g.next = 87654
                srec_no.a.next = True
                srec_no.b.next = False
                srec_no.c.next = "0011"
                srec_no.d.next = 7
                srec_no.e.next = 0
                srec_no.f.next = False
                srec_no.g.next = 87654

                vrec_res.a.value = True
                vrec_res.b.value = False
                vrec_res.c.value = "0011"
                vrec_res.d.value = 7
                vrec_res.e.value = 0
                vrec_res.f.value = False
                vrec_res.g.value = 87654
                vrec_no.a.value = True
                vrec_no.b.value = False
                vrec_no.c.value = "0011"
                vrec_no.d.value = 7
                vrec_no.e.value = 0
                vrec_no.f.value = False
                vrec_no.g.value = 87654


#
# test code
#
std.VhdlCompiler.to_string(test_reset_03)


class PortSet:
    def __init__(self, dut, prefix):
        for name in "abcdefg":
            setattr(self, f"res_{name}", getattr(dut, f"{prefix}_res_{name}"))
            setattr(self, f"no_{name}", getattr(dut, f"{prefix}_no_{name}"))

    def check(self, mode: str):
        match mode:
            case "initial" | "reset":
                assert self.res_a.value == 0
                assert self.res_b.value == 1
                assert self.res_c.value == 12
                assert self.res_d.value == 23
                assert self.res_e.value == (0b1000 - 3)
                assert self.res_f.value == 1
                assert self.res_g.value == 1235
            case "set":
                assert self.res_a.value == 1
                assert self.res_b.value == 0
                assert self.res_c.value == 3
                assert self.res_d.value == 7
                assert self.res_e.value == 0
                assert self.res_f.value == 0
                assert self.res_g.value == 87654
            case _:
                raise AssertionError("invalid mode")

        match mode:
            case "initial":
                assert self.no_a.value == 0
                assert self.no_b.value == 1
                assert self.no_c.value == 12
                assert self.no_d.value == 23
                assert self.no_e.value == (0b1000 - 3)
                assert self.no_f.value == 1
                assert self.no_g.value == 1235
            case "set" | "reset":
                assert self.no_a.value == 1
                assert self.no_b.value == 0
                assert self.no_c.value == 3
                assert self.no_d.value == 7
                assert self.no_e.value == 0
                assert self.no_f.value == 0
                assert self.no_g.value == 87654
            case _:
                raise AssertionError("invalid mode")


@cocotb_util.test()
async def testbench_reset_03(dut: test_reset_03):
    dut.set.value = 0
    dut.reset.value = 0

    set_port = PortSet(dut, "port")
    set_sig = PortSet(dut, "sig")
    set_var = PortSet(dut, "var")
    set_srec = PortSet(dut, "srec")
    set_vrec = PortSet(dut, "vrec")

    async def check(mode):
        await cocotb_util.step()

        for _ in range(3):
            set_port.check(mode)
            set_sig.check(mode)
            set_var.check(mode)
            set_srec.check(mode)
            set_vrec.check(mode)
            await cocotb_util.step()

    await check("initial")

    dut.reset.value = 1
    await check("initial")

    dut.set.value = 1
    await check("initial")

    dut.reset.value = 0
    await check("set")

    dut.set.value = 0
    await check("set")

    dut.reset.value = 1
    await check("reset")

    dut.reset.value = 0
    await check("reset")

    dut.set.value = 1
    await check("set")


class Unittest(unittest.TestCase):
    def test_reset_03(self):
        global reset_active_low, reset_async
        reset_active_low = True
        reset_async = True
        cocotb_util.run_cocotb_tests(
            test_reset_03,
            __file__,
            self.__module__,
        )
