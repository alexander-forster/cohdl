from __future__ import annotations

import unittest

import cohdl
from cohdl import std, BitVector, Unsigned, Port

from cohdl_testutil import cocotb_util

LEN_A = 1
LEN_B = 2
LEN_C = 3
LEN_D = 8


class test_roll(cohdl.Entity):
    inp_a = Port.input(BitVector[LEN_A])
    inp_b = Port.input(BitVector[LEN_B])
    inp_c = Port.input(BitVector[LEN_C])
    inp_d = Port.input(BitVector[LEN_D])

    def architecture(self):
        inputs = (self.inp_a, self.inp_b, self.inp_c, self.inp_d)

        for inp in inputs:
            width = inp.width

            for w in range(width + 1):
                out_rol = std.add_entity_port(
                    self, Port.output(std.base_type(inp), name=f"rol_{width}_{w}")
                )

                out_ror = std.add_entity_port(
                    self, Port.output(std.base_type(inp), name=f"ror_{width}_{w}")
                )

                @std.concurrent
                def logic():
                    out_rol.next = std.rol(inp, w)
                    out_ror.next = std.ror(inp, w)


#
# test code
#


@cocotb_util.test()
async def testbench_roll(dut: test_roll):
    for input in range(256):
        dut.inp_a.value = input % 2**LEN_A
        dut.inp_b.value = input % 2**LEN_B
        dut.inp_c.value = input % 2**LEN_C
        dut.inp_d.value = input % 2**LEN_D

        await cocotb_util.step()

        for w in (LEN_A, LEN_B, LEN_C, LEN_D):
            inp = f"{input%2**w:0{w}b}"

            for shift in range(w + 1):
                str_rol = inp[shift:] + inp[0:shift]
                str_ror = inp[-shift:] + inp[0:-shift]

                name_rol = f"rol_{w}_{shift}"
                name_ror = f"ror_{w}_{shift}"

                port_rol = getattr(dut, name_rol).value.binstr
                port_ror = getattr(dut, name_ror).value.binstr

                assert port_rol == str_rol, f"{inp} {name_rol}"
                assert port_ror == str_ror, f"{inp} {name_ror}"


class Unittest(unittest.TestCase):
    def test_hdl(self):
        cocotb_util.run_cocotb_tests(test_roll, __file__, self.__module__)

    def test_python(self):
        for w in range(1, 5):
            for nr in range(2**w):
                for shift in range(w + 1):
                    inp = f"{nr:0{w}b}"

                    str_rol = inp[shift:] + inp[0:shift]
                    str_ror = inp[-shift:] + inp[0:-shift]

                    inp_bv = Unsigned[w](nr)

                    assert str_rol == str(std.rol(inp_bv, shift))
                    assert str_ror == str(std.ror(inp_bv, shift))
