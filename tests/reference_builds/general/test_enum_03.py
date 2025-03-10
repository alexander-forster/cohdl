import unittest

import cohdl
from cohdl import BitVector, Port, Signal, Bit, select_with
from cohdl import std, enum


from cohdl_testutil import cocotb_util


class MyEnum(enum.Enum):
    a = enum.auto()
    b = enum.auto()
    c = enum.auto()
    d = enum.auto()


class test_enum_03(cohdl.Entity):
    inp_1 = Port.input(BitVector[2])
    inp_2 = Port.input(BitVector[2])

    is_a = Port.output(Bit)
    is_b = Port.output(Bit)
    is_c = Port.output(Bit)
    is_d = Port.output(Bit)

    is_not_a = Port.output(Bit)
    is_not_b = Port.output(Bit)
    is_not_c = Port.output(Bit)
    is_not_d = Port.output(Bit)

    is_same = Port.output(Bit)
    is_not_same = Port.output(Bit)

    def architecture(self):
        sig_1 = Signal[MyEnum]()
        sig_2 = Signal[MyEnum]()

        enum_map = {
            "00": MyEnum.a,
            "01": MyEnum.b,
            "10": MyEnum.c,
            "11": MyEnum.d,
        }

        @std.concurrent
        def logic_select_enum():
            sig_1.next = select_with(self.inp_1, enum_map, default=MyEnum.a)
            sig_2.next = select_with(self.inp_2, enum_map, default=MyEnum.a)

            self.is_a <<= sig_1 == MyEnum.a
            self.is_b <<= MyEnum.b == sig_1
            self.is_c <<= sig_1 == MyEnum.c
            self.is_d <<= MyEnum.d == sig_1

            self.is_not_a <<= sig_1 != MyEnum.a
            self.is_not_b <<= MyEnum.b != sig_1
            self.is_not_c <<= sig_1 != MyEnum.c
            self.is_not_d <<= MyEnum.d != sig_1

            self.is_same <<= sig_1 == sig_2
            self.is_not_same <<= sig_1 != sig_2


#
# test code
#


@cocotb_util.test()
async def testbench_enum_03(dut: test_enum_03):
    inp_gen = cocotb_util.ConstrainedGenerator(2)

    for inp_1 in inp_gen.all():
        for inp_2 in inp_gen.all():
            cocotb_util.assign(dut.inp_1, inp_1)
            cocotb_util.assign(dut.inp_2, inp_2)
            await cocotb_util.step()

            assert dut.is_a.value == (inp_1 == 0)
            assert dut.is_b.value == (inp_1 == 1)
            assert dut.is_c.value == (inp_1 == 2)
            assert dut.is_d.value == (inp_1 == 3)

            assert dut.is_not_a.value == (inp_1 != 0)
            assert dut.is_not_b.value == (inp_1 != 1)
            assert dut.is_not_c.value == (inp_1 != 2)
            assert dut.is_not_d.value == (inp_1 != 3)

            assert dut.is_same.value == (inp_1 == inp_2)
            assert dut.is_not_same.value == (inp_1 != inp_2)


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_enum_03, __file__, self.__module__)
