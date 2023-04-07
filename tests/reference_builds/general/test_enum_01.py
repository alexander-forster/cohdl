import unittest

import cohdl
from cohdl import BitVector, Port, Signal, select_with
from cohdl import std, enum


from cohdl_testutil import cocotb_util


class MyEnum(enum.Enum):
    a = enum.auto()
    b = enum.auto()
    c = enum.auto()
    d = enum.auto()


class test_enum_01(cohdl.Entity):
    input_code = Port.input(BitVector[2])
    output_code = Port.output(BitVector[2])

    def architecture(self):
        my_enum = Signal[MyEnum]()

        @std.concurrent
        def logic_select_enum():
            my_enum.next = select_with(
                self.input_code,
                {
                    "00": MyEnum.a,
                    "01": MyEnum.b,
                    "10": MyEnum.c,
                    "11": MyEnum.d,
                },
                MyEnum.a,
            )

        @std.concurrent
        def logic_decode_enum():
            self.output_code <<= select_with(
                my_enum,
                {
                    MyEnum.a: "00",
                    MyEnum.b: "01",
                    MyEnum.c: "10",
                    MyEnum.d: "11",
                },
                cohdl.Null,
            )


#
# test code
#


@cocotb_util.test()
async def testbench_enum_01(dut: test_enum_01):
    inp_gen = cocotb_util.ConstrainedGenerator(2)

    for inp in inp_gen.all():
        cocotb_util.assign(dut.input_code, inp)
        await cocotb_util.step()

        assert dut.output_code.value == inp


class Unittest(unittest.TestCase):
    def test_base(self):
        cocotb_util.run_cocotb_tests(test_enum_01, __file__, self.__module__)
