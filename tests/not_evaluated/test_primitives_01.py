from typing import cast
import unittest

from cohdl._core._bit import Bit, BitState
from cohdl._core._bit_vector import BitVector
from cohdl._core._unsigned import Unsigned
from cohdl._core._signed import Signed
from cohdl._core._integer import Integer

from cohdl._core._type_qualifier import (
    Signal,
    Variable,
    Temporary,
)


class SynthesizableTester(unittest.TestCase):
    def test_synthesizable_basics(self):
        for primitive_type in [Bit, BitVector[16], Unsigned[16], Signed[16], Integer]:
            primitive = primitive_type()

            copy = primitive.copy()

            self.assertTrue(type(copy) is type(primitive))
            self.assertTrue(copy is not primitive)

            for Qualifier in [Signal, Variable, Temporary]:
                wrapped = Qualifier[primitive_type](primitive)

                self.assertFalse(wrapped.decay() is wrapped)
                self.assertTrue(wrapped.type is primitive_type)
                self.assertTrue(wrapped.qualifier is Qualifier)
                self.assertTrue(wrapped._root is wrapped)
                self.assertTrue(len(wrapped._ref_spec) == 0)

    def test_assignment(self):
        def signal_next(obj, value):
            s = Signal[type(obj)]()
            s.next = value

        def signal_ilshift(obj, value):
            s = Signal[type(obj)](obj)
            s <<= value

        def check_invalid(obj, *values):
            def impl(obj, values):
                for value in values:
                    self.assertRaises(AssertionError, obj._assign, value)
                    self.assertRaises(AssertionError, signal_next, obj, value)
                    self.assertRaises(AssertionError, signal_ilshift, obj, value)

            impl(obj, values)
            # impl(Variable[type(obj)](obj), *values)

        def check_valid(obj, *values):
            def impl(obj, values):
                for value in values:
                    obj._assign(value)
                    signal_next(obj, value)
                    signal_next(obj, value)

            impl(obj, values)
            # impl(Variable[type(obj)](obj), values)

        check_valid(Bit(), 0, 1, True, False, "0", "1", BitState.HIGH, Bit())

        check_invalid(
            Bit(),
            -1,
            2,
            3,
            [],
            {},
            "00",
            "11",
            "asdf",
            "A",
            "B",
            None,
            # Integer(1),
            BitVector[1](),
            BitVector[2](),
            Unsigned[1](),
            Unsigned[2](),
            Signed[1](),
            Signed[2](),
        )

        check_valid(BitVector[8](), BitVector[8](), Unsigned[8](), Signed[8]())
        check_invalid(
            BitVector[8](),
            BitVector[7](),
            BitVector[9](),
            BitVector[1](),
            Unsigned[7](),
            Unsigned[9](),
            Signed[7](),
            Signed[9](),
            Integer(),
            -1,
            0,
            1,
            2,
            3,
            [],
            {},
        )

        check_valid(
            Unsigned[8](),
            Unsigned[8](),
            Unsigned[7](),
            Unsigned[2](),
            Integer(0),
            Integer(1),
            Integer(255),
            0,
            1,
            2,
            255,
        )

        check_invalid(
            Unsigned[8](),
            BitVector[7](),
            BitVector[9](),
            BitVector[1](),
            Unsigned[9](),
            Signed[1](),
            Signed[2](),
            Signed[7](),
            Signed[9](),
            Integer(-1),
            Integer(256),
            -1,
            256,
            500,
            1000,
            [],
            {},
        )

        check_valid(
            Signed[8](),
            Signed[8](),
            Signed[7](),
            Signed[6](),
            Signed[1](),
            Unsigned[7](),
            Unsigned[3](),
            Unsigned[1](),
            Integer(-128),
            Integer(-1),
            Integer(),
            Integer(127),
            -128,
            -1,
            0,
            127,
        )

        check_invalid(
            Signed[8](),
            Signed[9](),
            Signed[16](),
            Unsigned[8](),
            Unsigned[9](),
            Unsigned[16](),
            BitVector[1](),
            BitVector[16](),
            Integer(-129),
            Integer(-1000),
            Integer(128),
            Integer(1000),
            -129,
            128,
            1000,
        )
