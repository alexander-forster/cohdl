import unittest

from cohdl import Bit, BitState


class BitStateTester(unittest.TestCase):
    def test_bool_conv(self):
        self.assertTrue(BitState.HIGH)
        self.assertFalse(BitState.LOW)

    def test_inv(self):
        self.assertTrue(~BitState.LOW is BitState.HIGH)
        self.assertTrue(~BitState.HIGH is BitState.LOW)

    def test_binop(self):

        h = BitState.HIGH
        l = BitState.LOW
        # reveal_type(h | l)

        # binary or
        self.assertTrue(l | l is l)
        self.assertTrue(l | h is h)
        self.assertTrue(h | l is h)
        self.assertTrue(h | h is h)

        # binary and
        self.assertTrue(l & l is l)
        self.assertTrue(l & h is l)
        self.assertTrue(h & l is l)
        self.assertTrue(h & h is h)

        # binary xor
        self.assertTrue(l ^ l is l)
        self.assertTrue(l ^ h is h)
        self.assertTrue(h ^ l is h)
        self.assertTrue(h ^ h is l)

    def test_tostr(self):
        self.assertTrue(str(BitState.LOW) == "0")
        self.assertTrue(str(BitState.HIGH) == "1")
        self.assertTrue(str(BitState.UNINITIALZED) == "U")
        self.assertTrue(str(BitState.UNKNOWN) == "X")
        self.assertTrue(str(BitState.HIGH_IMPEDANCE) == "Z")

    def test_fromstr(self):
        self.assertTrue(BitState.from_str("0") is BitState.LOW)
        self.assertTrue(BitState.from_str("1") is BitState.HIGH)
        self.assertTrue(BitState.from_str("U") is BitState.UNINITIALZED)
        self.assertTrue(BitState.from_str("X") is BitState.UNKNOWN)
        self.assertTrue(BitState.from_str("-") is BitState.DONT_CARE)

        self.assertRaises(AssertionError, BitState.construct, "")
        self.assertRaises(AssertionError, BitState.construct, "00")
        self.assertRaises(AssertionError, BitState.construct, "asdf")
        self.assertRaises(AssertionError, BitState.construct, "x")
        self.assertRaises(AssertionError, BitState.construct, "u")
        self.assertRaises(AssertionError, BitState.construct, "_")

    def test_construct(self):
        self.assertTrue(BitState.construct(False) is BitState.LOW)
        self.assertTrue(BitState.construct(True) is BitState.HIGH)

        self.assertTrue(BitState.construct(0) is BitState.LOW)
        self.assertTrue(BitState.construct(1) is BitState.HIGH)
        self.assertRaises(AssertionError, BitState.construct, 2)
        self.assertRaises(AssertionError, BitState.construct, -1)
        self.assertRaises(AssertionError, BitState.construct, -100)
        self.assertRaises(AssertionError, BitState.construct, 1000)

        self.assertTrue(BitState.construct("0") is BitState.LOW)
        self.assertTrue(BitState.construct("1") is BitState.HIGH)
        self.assertTrue(BitState.construct("U") is BitState.UNINITIALZED)
        self.assertTrue(BitState.construct("X") is BitState.UNKNOWN)
        self.assertTrue(BitState.construct("-") is BitState.DONT_CARE)

        self.assertRaises(AssertionError, BitState.construct, "")
        self.assertRaises(AssertionError, BitState.construct, "00")
        self.assertRaises(AssertionError, BitState.construct, "asdf")
        self.assertRaises(AssertionError, BitState.construct, "x")
        self.assertRaises(AssertionError, BitState.construct, "u")
        self.assertRaises(AssertionError, BitState.construct, "_")


class BitTester(unittest.TestCase):
    def test_init(self):
        def with_arg(arg, expected_bool: bool, expected_state: BitState):
            bit = Bit(arg)

            self.assertTrue(bool(bit) is expected_bool)
            self.assertTrue(bit.get() is expected_state)
            self.assertFalse(bit is Bit(arg))

            cpy = bit.copy()
            self.assertFalse(bit is cpy)
            self.assertTrue(bit.get() is cpy.get())

        with_arg(False, False, BitState.LOW)
        with_arg(True, True, BitState.HIGH)

        with_arg(0, False, BitState.LOW)
        with_arg(1, True, BitState.HIGH)

        with_arg("0", False, BitState.LOW)
        with_arg("1", True, BitState.HIGH)

        with_arg(BitState.LOW, False, BitState.LOW)
        with_arg(BitState.HIGH, True, BitState.HIGH)

        with_arg(Bit(BitState.LOW), False, BitState.LOW)
        with_arg(Bit(BitState.HIGH), True, BitState.HIGH)

    def test_copy(self):
        def copy_bit(bit):
            cpy = bit.copy()

            self.assertTrue(cpy is not bit)
            self.assertTrue(cpy.get() is bit.get())
            self.assertTrue(cpy == bit)

        args = [False, True, 0, 1, "0", "1"]

        for default_arg in args:
            bit = Bit(default_arg)
            copy_bit(bit)

    def test_invert(self):
        bit = Bit(False)

        a = bit.invert()
        self.assertTrue(isinstance(a, Bit))
        self.assertTrue(bit.get() is BitState.LOW)
        self.assertTrue(a.get() is BitState.HIGH)

        b = ~bit
        self.assertTrue(isinstance(b, Bit))
        self.assertTrue(bit.get() is BitState.LOW)
        self.assertTrue(b.get() is BitState.HIGH)

        a = a.invert()
        b = ~b

        self.assertTrue(a.get() is BitState.LOW)
        self.assertTrue(b.get() is BitState.LOW)

    def test_binop(self):
        def helper(result: Bit, expected):
            self.assertTrue(isinstance(result, Bit))
            self.assertTrue(bool(result) == expected)

        l = Bit(False)
        h = Bit(True)

        helper(l | l, False)
        helper(l | h, True)
        helper(h | l, True)
        helper(h | h, True)

        helper(l & l, False)
        helper(l & h, False)
        helper(h & l, False)
        helper(h & h, True)

        helper(l ^ l, False)
        helper(l ^ h, True)
        helper(h ^ l, True)
        helper(h ^ h, False)

    def test_cmp(self):
        l = Bit(False)

        self.assertTrue(Bit(False) == Bit(False))
        self.assertTrue(Bit(True) == Bit(True))
        self.assertFalse(Bit(False) == Bit(True))
        self.assertFalse(Bit(True) == Bit(False))

        self.assertFalse(Bit(False) != Bit(False))
        self.assertFalse(Bit(True) != Bit(True))
        self.assertTrue(Bit(False) != Bit(True))
        self.assertTrue(Bit(True) != Bit(False))

        self.assertTrue(Bit(False) == BitState.LOW)
        self.assertTrue(Bit(True) == BitState.HIGH)
        self.assertFalse(Bit(False) == BitState.HIGH)
        self.assertFalse(Bit(True) == BitState.LOW)

        self.assertFalse(Bit(False) != BitState.LOW)
        self.assertFalse(Bit(True) != BitState.HIGH)
        self.assertTrue(Bit(False) != BitState.HIGH)
        self.assertTrue(Bit(True) != BitState.LOW)

        self.assertTrue(BitState.LOW == Bit(False))
        self.assertTrue(BitState.HIGH == Bit(True))
        self.assertFalse(BitState.LOW == Bit(True))
        self.assertFalse(BitState.HIGH == Bit(False))

        self.assertFalse(BitState.LOW != Bit(False))
        self.assertFalse(BitState.HIGH != Bit(True))
        self.assertTrue(BitState.LOW != Bit(True))
        self.assertTrue(BitState.HIGH != Bit(False))
