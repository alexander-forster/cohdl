import unittest

import cohdl
from cohdl import BitVector, Port, Signal
from cohdl import std, enum


from cohdl_testutil import cocotb_util


class MyEnum(enum.Enum):
    a = enum.auto()
    b = enum.auto()
    c = enum.auto()
    d = enum.auto()


class test_enum_02(cohdl.Entity):
    input_code = Port.input(BitVector[2])
    output_code = Port.output(BitVector[2])

    def architecture(self):
        my_enum = Signal[MyEnum]()

        @std.sequential
        def logic_select_enum():
            match self.input_code:
                case "00":
                    my_enum.next = MyEnum.a
                case "01":
                    my_enum.next = MyEnum.b
                case "10":
                    my_enum.next = MyEnum.c
                case "11":
                    my_enum.next = MyEnum.d
                case _:
                    my_enum.next = MyEnum.a

        @std.sequential
        def logic_decode_enum():
            match my_enum:
                case MyEnum.a:
                    self.output_code <<= "00"
                case MyEnum.b:
                    self.output_code <<= "01"
                case MyEnum.c:
                    self.output_code <<= "10"
                case MyEnum.d:
                    self.output_code <<= "11"
                case _:
                    self.output_code <<= "00"


#
# test code
#


@cocotb_util.test()
async def testbench_enum_02(dut: test_enum_02):
    inp_gen = cocotb_util.ConstrainedGenerator(2)

    for inp in inp_gen.all():
        cocotb_util.assign(dut.input_code, inp)
        await cocotb_util.step()

        assert dut.output_code.value == inp


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_enum_02, __file__, self.__module__)
