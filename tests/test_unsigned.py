import unittest
import random

from cohdl import Unsigned, BitOrder


class UnsignedTester(unittest.TestCase):
    def test_init(self):
        for w in (1, 2, 3, 15, 37, 128):
            for x in [random.randint(0, 2**w - 1) for _ in range(25)]:
                val = Unsigned[w](x)

                for cmp in (val, x, Unsigned[w](val)):
                    self.assertTrue(val == cmp)
                    self.assertTrue(cmp == val)
                    self.assertTrue(cmp - val == 0)
                    self.assertTrue(val - cmp == 0)
                    self.assertTrue(0 == cmp - val)
                    self.assertTrue(0 == val - cmp)

                    self.assertFalse(cmp != val)
                    self.assertFalse(val != cmp)

                    self.assertFalse(cmp < val)
                    self.assertFalse(val < cmp)
                    self.assertFalse(cmp > val)
                    self.assertFalse(val > cmp)

                    self.assertTrue(cmp <= val)
                    self.assertTrue(val <= cmp)
                    self.assertTrue(cmp >= val)
                    self.assertTrue(val >= cmp)

    def test_init_asserts(self):
        for w in (1, 2, 3, 15, 1024):
            # TODO: test or remove order
            for order in (BitOrder.DOWNTO, BitOrder.UPTO):
                self.assertRaises(AssertionError, Unsigned[w], -1)
                self.assertRaises(AssertionError, Unsigned[w], -17)
                self.assertRaises(AssertionError, Unsigned[w], 2**w)
                self.assertRaises(
                    AssertionError,
                    Unsigned[w],
                    2**w + 53225265256,
                )
                self.assertRaises(
                    AssertionError,
                    Unsigned[w],
                    "0" * (w - 1),
                )
                self.assertRaises(
                    AssertionError,
                    Unsigned[w],
                    "00000" * (w + 1),
                )
