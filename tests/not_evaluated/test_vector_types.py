import unittest

from cohdl import Unsigned, Signed, Unsigned, BitVector, Null, Full


class TestVectorTypes(unittest.TestCase):

    def test_inheritance(self):
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

    def test_constructors(self):
        for target_w in (1, 2, 4):
            for src_w in (1, 2, 3, 5):
                if target_w >= src_w:
                    Unsigned[target_w](Unsigned[src_w]())
                else:
                    self.assertRaises(
                        AssertionError, Unsigned[target_w], Unsigned[src_w]()
                    )

                self.assertRaises(AssertionError, Unsigned[target_w], Signed[src_w]())

        for target_w in (1, 2, 4):
            for src_w in (1, 2, 3, 5):
                if target_w >= src_w:
                    Signed[target_w](Signed[src_w]())
                else:
                    self.assertRaises(AssertionError, Signed[target_w], Signed[src_w]())

                if target_w > src_w:
                    Signed[target_w](Unsigned[src_w]())
                else:
                    self.assertRaises(
                        AssertionError, Signed[target_w], Unsigned[src_w]()
                    )

    def test_compare(self):

        for w in (1, 2, 3, 8, 9):
            assert Signed[w](0) == 0
            assert Signed[w](0) == Null
            assert Signed[w](-1) == Full

        ...
