import unittest

from cohdl import std
from cohdl import BitVector


class OneHotTester(unittest.TestCase):
    def test_one_hot(self):
        for width in (1, 2, 3, 4, 8, 16):
            for bit in range(width):
                vec = std.one_hot(width, bit)

                assert len(vec) == width

                for nr, b in enumerate(vec):
                    if nr == bit:
                        assert b
                    else:
                        assert not b

            for bit in (-1, -123, width + 1, width + 2, width + 123):
                self.assertRaises(AssertionError, std.one_hot, width, bit)
