import unittest

from cohdl import (
    Unsigned,
    Signed,
    Unsigned,
    BitVector,
)


class TestInheritance(unittest.TestCase):

    def test_vectors(self):
        for w in range(1, 8):
            self.assertTrue(issubclass(BitVector[w], BitVector))

            self.assertTrue(issubclass(Unsigned[w], BitVector))
            self.assertTrue(issubclass(Unsigned[w], Unsigned))
            self.assertTrue(issubclass(Unsigned[w], BitVector[w]))
            self.assertTrue(issubclass(Unsigned[w], Unsigned[w]))

            self.assertTrue(issubclass(Signed[w], BitVector))
            self.assertTrue(issubclass(Signed[w], Signed))
            self.assertTrue(issubclass(Signed[w], BitVector[w]))
            self.assertTrue(issubclass(Signed[w], Signed[w]))

            self.assertFalse(issubclass(BitVector[w], BitVector[w + 1]))
            self.assertFalse(issubclass(Unsigned[w], Unsigned[w + 1]))
            self.assertFalse(issubclass(Signed[w], Signed[w + 1]))

            self.assertFalse(issubclass(BitVector[w], Unsigned[w]))
            self.assertFalse(issubclass(BitVector[w], Signed[w]))
            self.assertFalse(issubclass(Unsigned[w], Signed[w]))
            self.assertFalse(issubclass(Signed[w], Unsigned[w]))
