import unittest

from cohdl import std
from cohdl import Bit, BitVector, Signed, Unsigned, Signal, Variable, Temporary

import random


def rand_str(width):
    return "".join(random.choices("01", k=width))


class Tester(unittest.TestCase):
    def test_zeros(self):
        for width in (1, 2, 3, 4, 8, 16):
            vec = std.zeros(width)

            assert vec.width == width
            assert len(vec) == width
            assert not vec
            assert ~vec
            assert vec == BitVector[width]("0" * width)
            assert str(vec) == "0" * width

    def test_ones(self):
        for width in (1, 2, 3, 4, 8, 16):
            vec = std.ones(width)

            assert vec.width == width
            assert len(vec) == width
            assert vec
            assert not ~vec
            assert vec == BitVector[width]("1" * width)
            assert str(vec) == "1" * width

    def test_width(self):
        def identity(arg):
            return arg

        def arg_generator(width: int):
            if width == 1:
                return [Bit(), BitVector[width](), Signed[width](), Unsigned[width]()]
            else:
                return [BitVector[width](), Signed[width](), Unsigned[width]()]

        for Qualifier in (identity, Signal, Variable, Temporary):
            for width in (1, 2, 3, 4, 8, 128):
                for arg in arg_generator(width):
                    assert std.width(Qualifier(arg)) == width
