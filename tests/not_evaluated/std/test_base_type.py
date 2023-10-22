import unittest

from cohdl import std
from cohdl import (
    Array,
    BitVector,
    Bit,
    Unsigned,
    Signed,
    Integer,
    Boolean,
    Signal,
    Variable,
    Temporary,
)


class OneHotTester(unittest.TestCase):
    def test_basetype(self):
        assert std.base_type(int) is int
        assert std.base_type(1) is int
        assert std.base_type(Bit()) is Bit
        assert std.base_type(BitVector[5]()) is BitVector[5]
        assert std.base_type(Array[Bit, 5]) is Array[Bit, 5]

        #
        #
        #

        assert std.base_type(Signal[Bit]) is Bit
        assert std.base_type(Signal[Array[Bit, 3]]) is Array[Bit, 3]
        assert std.base_type(Signal[BitVector[1]]) is BitVector[1]
        assert std.base_type(Variable[BitVector[2:0]]) is BitVector[3]
        assert std.base_type(Temporary[BitVector[7:0]]) is BitVector[8]
        assert std.base_type(Signal[BitVector[50]]) is BitVector[49:0]

        assert std.base_type(Signal[Unsigned[1]]) is Unsigned[1]
        assert std.base_type(Variable[Unsigned[2:0]]) is Unsigned[3]
        assert std.base_type(Signal[Unsigned[7:0]]) is Unsigned[8]
        assert std.base_type(Temporary[Unsigned[50]]) is Unsigned[49:0]

        assert std.base_type(Signal[Signed[1]]) is Signed[1]
        assert std.base_type(Variable[Signed[2:0]]) is Signed[3]
        assert std.base_type(Signal[Signed[7:0]]) is Signed[8]
        assert std.base_type(Temporary[Signed[50]]) is Signed[49:0]

        assert std.base_type(Signal[int]) is Integer
        assert std.base_type(Variable[bool]) is Boolean

        #
        #
        #

        assert std.base_type(Signal[Bit]()) is Bit
        assert std.base_type(Signal[BitVector[1]]()) is BitVector[1]
        assert std.base_type(Variable[BitVector[2:0]]()) is BitVector[3]
        assert std.base_type(Temporary[BitVector[7:0]]()) is BitVector[8]
        assert std.base_type(Signal[BitVector[50]]()) is BitVector[49:0]

        assert std.base_type(Signal[Unsigned[1]]()) is Unsigned[1]
        assert std.base_type(Variable[Unsigned[2:0]]()) is Unsigned[3]
        assert std.base_type(Signal[Unsigned[7:0]]()) is Unsigned[8]
        assert std.base_type(Temporary[Unsigned[50]]()) is Unsigned[49:0]

        assert std.base_type(Signal[Signed[1]]()) is Signed[1]
        assert std.base_type(Variable[Signed[2:0]]()) is Signed[3]
        assert std.base_type(Signal[Signed[7:0]]()) is Signed[8]
        assert std.base_type(Temporary[Signed[50]]()) is Signed[49:0]

        assert std.base_type(Signal[int]()) is Integer
        assert std.base_type(Variable[bool]()) is Boolean
