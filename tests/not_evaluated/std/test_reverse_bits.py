import unittest

from cohdl import std
from cohdl import BitVector

import random


def rand_str(width):
    return "".join(random.choices("01", k=width))


class ReverseBitRester(unittest.TestCase):
    def test_reverse_bits(self):
        for width in (1, 2, 3, 4, 8, 16):
            for _ in range(8):
                bit_str = rand_str(width)

                vec = BitVector[width](bit_str)
                vec_rev = BitVector[width](bit_str[::-1])

                assert vec_rev == std.reverse_bits(vec)
