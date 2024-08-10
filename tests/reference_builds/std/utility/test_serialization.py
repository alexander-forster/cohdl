from __future__ import annotations

import unittest

import cohdl
from cohdl import (
    std,
    Bit,
    BitVector,
    Unsigned,
    Signed,
    Port,
    Null,
    Full,
    Array,
    Boolean,
)

from cohdl_testutil import cocotb_util

import os


class UseExternalRefQualifierHint:
    pass


class UseDefaultQualifierHint:
    pass


deserialization_qualifier = eval(
    os.getenv("cohdl_test_deserialization_qualifier", "None")
)


class BaseRecord(std.Record):
    a: Bit


class DerivedEmpty(BaseRecord):
    pass


class DerivedBit(BaseRecord):
    b: Bit


class SubDerivedBitEmpty(DerivedBit):
    pass


class SubDerivedBit(DerivedBit):
    c: Signed[7]


class DerivedBitVector(BaseRecord):
    b: BitVector[15]


class RecordBool(std.Record):
    a: bool


class RecordInt(std.Record):
    a: int


class RecordArray(std.Record):
    a: std.Array[Bit, 4]


class RecordRawArray(std.Record):
    a: Array[BitVector[4], 3]


@cohdl.pyeval
def random_bv(width):
    rnd = cocotb_util.ConstrainedGenerator(width).random()
    return std.as_bitvector(rnd.as_str())


def check_fail(fn, err_type):
    try:
        fn()
    except err_type:
        return True
    return False


def check_serialization(T, width, trivial):
    if width != 0:
        cohdl.static_assert(std.count_bits(T) == width)

        if T is bool:
            cohdl.static_assert(std.count_bits(T(False)) == width)
        elif T is RecordBool:
            cohdl.static_assert(std.count_bits(T(a=True)) == width)
        else:
            cohdl.static_assert(std.count_bits(T()) == width)

        bv = random_bv(width)

        deserialized = std.from_bits[T](bv)

        if T is bool:
            cohdl.static_assert(isinstance(deserialized, Boolean))
        else:
            cohdl.static_assert(isinstance(deserialized, T))

        serialized = std.to_bits(deserialized)

        cohdl.static_assert(type(serialized) is BitVector[width])
        cohdl.static_assert(serialized == bv)

    if not cohdl.evaluated():
        std.exception.StdException.print_exception_infos(False)

        if width == 0:
            assert check_fail(
                lambda: std.count_bits(T), std.exception.SerializationFail
            )
            assert check_fail(
                lambda: std.count_bits(T()), std.exception.SerializationFail
            )

        else:
            assert not trivial == check_fail(
                lambda: std.from_bits[T](bv, qualifier=std.Ref),
                std.exception.RefQualifierFail,
            )

            std.exception.StdException.print_exception_infos(True)


def basic_check():
    for type, width, trivial in [
        (Bit, 1, True),
        (BitVector[1], 1, True),
        (BitVector[2], 2, True),
        (BitVector[17], 17, True),
        (Signed[1], 1, True),
        (Signed[9], 9, True),
        (Signed[33], 33, True),
        (Unsigned[1], 1, True),
        (Unsigned[5], 5, True),
        (Unsigned[7], 7, True),
        (Array[Bit, 1], 1, False),
        (Array[Bit, 4], 4, False),
        (Array[BitVector[3:0], 1], 4, False),
        (Array[Unsigned[6:0], 3], 21, False),
        (Array[Array[Bit, 5], 2], 10, False),
        (Array[Array[Signed[4], 4], 3], 48, False),
        (Array[Array[Array[Bit, 5], 3], 2], 30, False),
        (Array[Array[Array[Signed[2], 4], 4], 3], 96, False),
        (BaseRecord, 1, True),
        (DerivedEmpty, 1, True),
        (DerivedBit, 2, True),
        (SubDerivedBitEmpty, 2, True),
        (SubDerivedBit, 9, True),
        (DerivedBitVector, 16, True),
        (RecordBool, 1, False),
        (RecordInt, 0, False),
        (RecordArray, 4, False),
        (RecordRawArray, 12, False),
        (bool, 1, False),
        (int, 0, False),
    ]:
        check_serialization(type, width, trivial)


class test_serialization(cohdl.Entity):
    input_vector = Port.input(BitVector[16])

    out_bit = Port.output(Bit)
    out_bitvector = Port.output(BitVector[8])
    out_unsigned = Port.output(Unsigned[5])
    out_signed = Port.output(Signed[11])
    out_bool = Port.output(Bit)
    out_bool_2 = Port.output(Bit)

    out_arr_bit_0 = Port.output(Bit)
    out_arr_bit_1 = Port.output(Bit)

    out_std_arr_bit_0 = Port.output(Bit)
    out_std_arr_bit_1 = Port.output(Bit)

    out_arr_arr_bv_0_0 = Port.output(BitVector[2])
    out_arr_arr_bv_0_1 = Port.output(BitVector[2])
    out_arr_arr_bv_1_0 = Port.output(BitVector[2])
    out_arr_arr_bv_1_1 = Port.output(BitVector[2])
    out_arr_arr_bv_2_0 = Port.output(BitVector[2])
    out_arr_arr_bv_2_1 = Port.output(BitVector[2])

    out_rec_base_a = Port.output(Bit)

    out_rec_derived_empty_a = Port.output(Bit)

    out_rec_derived_bit_a = Port.output(Bit)
    out_rec_derived_bit_b = Port.output(Bit)

    out_rec_subderived_bit_empty_a = Port.output(Bit)
    out_rec_subderived_bit_empty_b = Port.output(Bit)

    out_rec_subderived_bit_a = Port.output(Bit)
    out_rec_subderived_bit_b = Port.output(Bit)
    out_rec_subderived_bit_c = Port.output(Signed[7])

    out_rec_derived_bv_a = Port.output(Bit)
    out_rec_derived_bv_b = Port.output(BitVector[15])

    out_rec_bool = Port.output(bool)

    out_rec_arr_0 = Port.output(Bit)
    out_rec_arr_1 = Port.output(Bit)
    out_rec_arr_2 = Port.output(Bit)
    out_rec_arr_3 = Port.output(Bit)

    out_rec_raw_arr_0 = Port.output(BitVector[4])
    out_rec_raw_arr_1 = Port.output(BitVector[4])
    out_rec_raw_arr_2 = Port.output(BitVector[4])

    def from_inp(self, T, no_ref=False):
        if deserialization_qualifier is UseDefaultQualifierHint:
            return std.from_bits[T](self.input_vector[std.count_bits(T) - 1 : 0])
        elif (
            deserialization_qualifier is std.Ref
            or deserialization_qualifier is UseExternalRefQualifierHint
        ):
            if no_ref:
                return std.from_bits[T](self.input_vector[std.count_bits(T) - 1 : 0])
            else:
                return std.from_bits[T](
                    self.input_vector[std.count_bits(T) - 1 : 0], qualifier=std.Ref
                )
        else:
            return std.from_bits[T](
                self.input_vector[std.count_bits(T) - 1 : 0],
                qualifier=deserialization_qualifier,
            )

    def check_non_trivial(self):
        @std.concurrent
        def logic():
            self.out_bool <<= self.from_inp(bool, no_ref=True)
            self.out_bool_2 <<= self.from_inp(Boolean, no_ref=True)

            x_arr_bit = self.from_inp(Array[Bit, 2], no_ref=True)
            self.out_arr_bit_0 <<= x_arr_bit[0]
            self.out_arr_bit_1 <<= x_arr_bit[1]

            x_std_arr_bit = self.from_inp(std.Array[Bit, 2], no_ref=True)
            self.out_std_arr_bit_0 <<= x_std_arr_bit[0]
            self.out_std_arr_bit_1 <<= x_std_arr_bit[1]

            x_arr_arr_bv = self.from_inp(Array[Array[BitVector[2], 2], 3], no_ref=True)
            x_arr_arr_bv_std = self.from_inp(
                std.Array[Array[BitVector[2], 2], 3], no_ref=True
            )
            x_arr_arr_bv_std_std = self.from_inp(
                std.Array[std.Array[BitVector[2], 2], 3], no_ref=True
            )

            self.out_arr_arr_bv_0_0 <<= x_arr_arr_bv[0][0]
            self.out_arr_arr_bv_1_1 <<= x_arr_arr_bv[1][1]
            self.out_arr_arr_bv_0_1 <<= x_arr_arr_bv_std[0][1]
            self.out_arr_arr_bv_2_0 <<= x_arr_arr_bv_std[2][0]
            self.out_arr_arr_bv_1_0 <<= x_arr_arr_bv_std_std[1][0]
            self.out_arr_arr_bv_2_1 <<= x_arr_arr_bv_std_std[2][1]

            self.out_rec_bool <<= self.from_inp(RecordBool, no_ref=True).a

            x_rec_arr = self.from_inp(RecordArray, no_ref=True)
            self.out_rec_arr_0 <<= x_rec_arr.a[0]
            self.out_rec_arr_1 <<= x_rec_arr.a[1]
            self.out_rec_arr_2 <<= x_rec_arr.a[2]
            self.out_rec_arr_3 <<= x_rec_arr.a[3]

            x_rec_raw_arr = self.from_inp(RecordRawArray, no_ref=True)
            self.out_rec_raw_arr_0 <<= x_rec_raw_arr.a[0]
            self.out_rec_raw_arr_1 <<= x_rec_raw_arr.a[1]
            self.out_rec_raw_arr_2 <<= x_rec_raw_arr.a[2]

    def check_trivial(self):
        @std.concurrent
        def logic():
            self.out_bit <<= self.from_inp(Bit)
            self.out_bitvector <<= self.from_inp(BitVector[8])
            self.out_unsigned <<= self.from_inp(Unsigned[5])
            self.out_signed <<= self.from_inp(Signed[11])

            self.out_rec_base_a <<= self.from_inp(BaseRecord).a

            self.out_rec_derived_empty_a <<= self.from_inp(DerivedEmpty).a

            x_derived_bit = self.from_inp(DerivedBit)
            self.out_rec_derived_bit_a <<= x_derived_bit.a
            self.out_rec_derived_bit_b <<= x_derived_bit.b

            x_subderived_bit_empty = self.from_inp(SubDerivedBitEmpty)
            self.out_rec_subderived_bit_empty_a <<= x_subderived_bit_empty.a
            self.out_rec_subderived_bit_empty_b <<= x_subderived_bit_empty.b

            x_subderived_bit = self.from_inp(SubDerivedBit)
            self.out_rec_subderived_bit_a <<= x_subderived_bit.a
            self.out_rec_subderived_bit_b <<= x_subderived_bit.b
            self.out_rec_subderived_bit_c <<= x_subderived_bit.c

            x_rec_derived_bv = self.from_inp(DerivedBitVector)
            self.out_rec_derived_bv_a <<= x_rec_derived_bv.a
            self.out_rec_derived_bv_b <<= x_rec_derived_bv.b

    def check_trivial_external(self):
        out_bit = self.from_inp(Bit)
        out_bitvector = self.from_inp(BitVector[8])
        out_unsigned = self.from_inp(Unsigned[5])
        out_signed = self.from_inp(Signed[11])

        out_rec_base = self.from_inp(BaseRecord)

        out_rec_derived_empty_a = self.from_inp(DerivedEmpty).a

        x_derived_bit = self.from_inp(DerivedBit)
        x_subderived_bit_empty = self.from_inp(SubDerivedBitEmpty)
        x_subderived_bit = self.from_inp(SubDerivedBit)
        x_rec_derived_bv = self.from_inp(DerivedBitVector)

        @std.concurrent
        def logic():
            self.out_bit <<= out_bit
            self.out_bitvector <<= out_bitvector
            self.out_unsigned <<= out_unsigned
            self.out_signed <<= out_signed

            self.out_rec_base_a <<= out_rec_base.a
            self.out_rec_derived_empty_a <<= out_rec_derived_empty_a

            self.out_rec_derived_bit_a <<= x_derived_bit.a
            self.out_rec_derived_bit_b <<= x_derived_bit.b

            self.out_rec_subderived_bit_empty_a <<= x_subderived_bit_empty.a
            self.out_rec_subderived_bit_empty_b <<= x_subderived_bit_empty.b

            self.out_rec_subderived_bit_a <<= x_subderived_bit.a
            self.out_rec_subderived_bit_b <<= x_subderived_bit.b
            self.out_rec_subderived_bit_c <<= x_subderived_bit.c

            self.out_rec_derived_bv_a <<= x_rec_derived_bv.a
            self.out_rec_derived_bv_b <<= x_rec_derived_bv.b

    def architecture(self):
        assert deserialization_qualifier is not None

        # check serialization of constants in python contexts
        basic_check()

        @std.concurrent
        def logic():
            # check serialization of constants in evaluated context
            basic_check()

        if deserialization_qualifier is UseExternalRefQualifierHint:
            self.check_trivial_external()
        else:
            self.check_trivial()

        self.check_non_trivial()


#
# test code
#


@cocotb_util.test()
async def testbench_serialization(dut: test_serialization):
    for rnd in cocotb_util.ConstrainedGenerator(16).random(64):

        await cocotb_util.check_concurrent(
            [
                (dut.input_vector, rnd),
            ],
            [
                (dut.out_bit, rnd.get_bit(0)),
                (dut.out_bitvector, rnd.get_slice(0, 7)),
                (dut.out_unsigned, rnd.get_slice(0, 4)),
                (dut.out_signed, rnd.get_slice(0, 10)),
                (dut.out_bool, rnd.get_slice(0, 0)),
                (dut.out_bool_2, rnd.get_slice(0, 0)),
                #
                (dut.out_arr_bit_0, rnd.get_bit(0)),
                (dut.out_arr_bit_1, rnd.get_bit(1)),
                #
                (dut.out_std_arr_bit_0, rnd.get_bit(0)),
                (dut.out_std_arr_bit_1, rnd.get_bit(1)),
                #
                (dut.out_arr_arr_bv_0_0, rnd.get_slice(0, 1)),
                (dut.out_arr_arr_bv_0_1, rnd.get_slice(2, 3)),
                (dut.out_arr_arr_bv_1_0, rnd.get_slice(4, 5)),
                (dut.out_arr_arr_bv_1_1, rnd.get_slice(6, 7)),
                (dut.out_arr_arr_bv_2_0, rnd.get_slice(8, 9)),
                (dut.out_arr_arr_bv_2_1, rnd.get_slice(10, 11)),
                #
                (dut.out_rec_base_a, rnd.get_bit(0)),
                #
                (dut.out_rec_derived_empty_a, rnd.get_bit(0)),
                #
                (dut.out_rec_derived_bit_a, rnd.get_bit(0)),
                (dut.out_rec_derived_bit_b, rnd.get_bit(1)),
                #
                (dut.out_rec_subderived_bit_empty_a, rnd.get_bit(0)),
                (dut.out_rec_subderived_bit_empty_b, rnd.get_bit(1)),
                #
                (dut.out_rec_subderived_bit_a, rnd.get_bit(0)),
                (dut.out_rec_subderived_bit_b, rnd.get_bit(1)),
                (dut.out_rec_subderived_bit_c, rnd.get_slice(2, 8)),
                #
                (dut.out_rec_derived_bv_a, rnd.get_bit(0)),
                (dut.out_rec_derived_bv_b, rnd.get_slice(1, 15)),
                #
                (dut.out_rec_arr_0, rnd.get_bit(0)),
                (dut.out_rec_arr_1, rnd.get_bit(1)),
                (dut.out_rec_arr_2, rnd.get_bit(2)),
                (dut.out_rec_arr_3, rnd.get_bit(3)),
                #
                (dut.out_rec_raw_arr_0, rnd.get_slice(0, 3)),
                (dut.out_rec_raw_arr_1, rnd.get_slice(4, 7)),
                (dut.out_rec_raw_arr_2, rnd.get_slice(8, 11)),
            ],
        )


class Unittest(unittest.TestCase):

    def test_serialization_default(self):
        global deserialization_qualifier

        deserialization_qualifier = UseDefaultQualifierHint

        cocotb_util.run_cocotb_tests(
            test_serialization,
            __file__,
            self.__module__,
            extra_env={
                "cohdl_test_deserialization_qualifier": "UseDefaultQualifierHint"
            },
        )

    def test_serialization_temp(self):
        global deserialization_qualifier

        deserialization_qualifier = std.Temporary

        cocotb_util.run_cocotb_tests(
            test_serialization,
            __file__,
            self.__module__,
            extra_env={"cohdl_test_deserialization_qualifier": "std.Temporary"},
        )

    def test_serialization_signal(self):
        global deserialization_qualifier

        deserialization_qualifier = std.Signal

        cocotb_util.run_cocotb_tests(
            test_serialization,
            __file__,
            self.__module__,
            extra_env={"cohdl_test_deserialization_qualifier": "std.Signal"},
        )

    def test_serialization_ref(self):
        global deserialization_qualifier

        deserialization_qualifier = std.Ref

        cocotb_util.run_cocotb_tests(
            test_serialization,
            __file__,
            self.__module__,
            extra_env={"cohdl_test_deserialization_qualifier": "std.Ref"},
        )

    def test_serialization_ext_ref(self):
        global deserialization_qualifier

        deserialization_qualifier = UseExternalRefQualifierHint

        cocotb_util.run_cocotb_tests(
            test_serialization,
            __file__,
            self.__module__,
            extra_env={
                "cohdl_test_deserialization_qualifier": "UseExternalRefQualifierHint"
            },
        )
