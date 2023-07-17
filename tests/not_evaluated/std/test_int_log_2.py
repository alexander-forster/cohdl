import unittest

from cohdl import std


class IntLog2Tester(unittest.TestCase):
    def test_int_log_2(self):
        for exp in range(100):
            self.assertEqual(std.int_log_2(2**exp), exp)

        self.assertRaises(AssertionError, std.int_log_2, 0)
        self.assertRaises(AssertionError, std.int_log_2, 3)
        self.assertRaises(AssertionError, std.int_log_2, -0)
        self.assertRaises(AssertionError, std.int_log_2, -1)
        self.assertRaises(AssertionError, std.int_log_2, -2)
        self.assertRaises(AssertionError, std.int_log_2, 1.0)
        self.assertRaises(AssertionError, std.int_log_2, 2.0)
