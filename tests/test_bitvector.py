import unittest
import random

from cohdl import BitVector, BitOrder, Bit, Null, Full
from cohdl._core._type_qualifier import (
    TypeQualifier,
    Variable,
    Signal,
    Temporary,
)


def rnd_bit_string(length):
    return "".join(["01U"[random.randint(0, 2)] for _ in range(length)])


class BitVectorTester(unittest.TestCase):
    def test_construction(self):
        def test(width, default=None, expected_assert=None):
            if expected_assert is not None:
                self.assertRaises(
                    expected_assert, lambda d: BitVector[width](d), default
                )
            else:
                a = BitVector[width](default)
                self.assertTrue(a.order is BitOrder.DOWNTO)
                self.assertTrue(a.width == width)
                self.assertTrue(len(a) == width)

                if isinstance(default, str):
                    self.assertTrue(default == str(a))

                b = BitVector[width](a)

                self.assertTrue(str(a) == str(b))

                for i in range(width):
                    self.assertTrue(isinstance(a[i], Bit))
                    self.assertTrue(isinstance(b[i], Bit))

                    self.assertTrue(a[i] == b[i])
                    self.assertFalse(a[i] is b[i])

                self.assertIsNot(a, b)

                rnd = BitVector[width](rnd_bit_string(width))

                prev_bits = [b[i] for i in range(width)]

                b._assign(rnd)

                for i in range(width):
                    # check, that subscript access returns reference
                    self.assertTrue(b[i] is prev_bits[i])
                    self.assertTrue(b[i] == rnd[i])
                    self.assertTrue(b[i] is not rnd[i])

                self.assertTrue(b == rnd)
                self.assertTrue(not b != rnd)

                b._assign(rnd)

                for i in range(width):
                    self.assertTrue(b[i] is prev_bits[i])

                self.assertTrue(b == rnd)
                self.assertTrue(rnd == b)

                for i in range(width):
                    self.assertTrue(b[i] is prev_bits[i])

                a._assign(rnd)

                self.assertTrue(b == a)
                self.assertTrue(a == b)

                self.assertRaises(AssertionError, b._assign, BitVector[width + 1]())

        for w in [1, 2, 3, 4, 5, 6, 7, 8, 16, 32, 37, 128, 1024, 0, -1, -2, -5, -100]:
            if w < 0:
                test(w, expected_assert=AssertionError)
                test(w, rnd_bit_string(w), expected_assert=AssertionError)
            else:
                test(w)
                test(w, rnd_bit_string(w))

                if w != 0:
                    test(w, " " * w, expected_assert=AssertionError)

                zeros = BitVector[w](Null)
                ones = BitVector[w](Full)
                rnd = BitVector[w](rnd_bit_string(w))

                test(w, zeros)
                test(w, ones)
                test(w, rnd)

    def test_cmp(self):
        for width in [1, 2, 4, 10, 16, 471, 1024]:
            ones = BitVector[width](Full)
            zeros = BitVector[width](Null)

            self.assertFalse(ones == zeros)
            self.assertFalse(zeros == ones)
            self.assertTrue(ones != zeros)
            self.assertTrue(zeros != ones)

    def test_msb_lsb_single(self):
        for category in [Signal, Variable, Temporary]:
            for order in [BitOrder.DOWNTO, BitOrder.UPTO]:
                for width in [1, 2, 4, 16, 423, 1024]:
                    v = category[BitVector[width]]()

                    lsb = v.lsb()
                    msb = v.msb()
                    left = v.left()
                    right = v.right()

                    self.assertTrue(issubclass(category, TypeQualifier))

                    self.assertIs(type(lsb).qualifier, category)
                    self.assertIs(type(msb).qualifier, category)
                    self.assertIs(type(left).qualifier, category)
                    self.assertIs(type(right).qualifier, category)

                    self.assertIs(type(lsb), category[Bit])
                    self.assertIs(type(msb), category[Bit])
                    self.assertIs(type(left), category[Bit])
                    self.assertIs(type(right), category[Bit])

                    self.assertIs(lsb._root, v)

                    lsb = lsb.get()
                    msb = msb.get()
                    left = left.get()
                    right = right.get()

                    self.assertTrue(isinstance(lsb, Bit))
                    self.assertTrue(isinstance(msb, Bit))
                    self.assertTrue(isinstance(left, Bit))
                    self.assertTrue(isinstance(right, Bit))

                    if width == 1:
                        self.assertTrue(lsb is msb is left is right)
                    else:
                        self.assertTrue(lsb is not msb)
                        self.assertTrue(left is not right)

                    if order is BitOrder.DOWNTO:
                        self.assertTrue(lsb is right)
                        self.assertTrue(msb is left)
                        self.assertTrue(lsb is v[0].get())
                        self.assertTrue(msb is v[width - 1].get())
                    else:
                        pass

    def test_msb_lsb_slice(self):
        v = BitVector[16]()

        self.assertRaises(AssertionError, v.lsb, 0)
        self.assertRaises(AssertionError, v.msb, 0)
        self.assertRaises(AssertionError, v.left, 0)
        self.assertRaises(AssertionError, v.right, 0)

        for i in range(1, v.width + 1):
            lsb = v.lsb(i)
            msb = v.msb(i)
            left = v.left(i)
            right = v.right(i)

            self.assertTrue(isinstance(lsb, BitVector))
            self.assertTrue(isinstance(msb, BitVector))
            self.assertTrue(isinstance(left, BitVector))
            self.assertTrue(isinstance(right, BitVector))

            self.assertTrue(lsb.order is BitOrder.DOWNTO)

            alias_lsb = right
            alias_msb = left

            for a, b in zip(lsb._value, alias_lsb._value):
                self.assertTrue(a is b)

            for a, b in zip(msb._value, alias_msb._value):
                self.assertTrue(a is b)

    def test_concat(self):
        for a in [1, 2, 5, 16]:
            for b in [1, 2, 5, 16]:
                str_a = rnd_bit_string(a)
                str_b = rnd_bit_string(b)

                bv_a = BitVector[a](str_a)
                bv_b = BitVector[b](str_b)

                concat = bv_a @ bv_b

                self.assertTrue(concat.width == a + b)
                self.assertTrue(concat == BitVector[a + b](str_a + str_b))

                bv_a._assign(BitVector[a](Null))
                bv_b._assign(BitVector[b](Null))

                self.assertTrue(
                    concat == BitVector[a + b](str_a + str_b),
                    "changing source does not affect output of operation",
                )

                concat._assign(BitVector[a + b](rnd_bit_string(a + b)))

                self.assertTrue(
                    bv_a == BitVector[a](Null),
                    "changing result does not affect input of operation",
                )
                self.assertTrue(
                    bv_b == BitVector[b](Null),
                    "changing result does not affect input of operation",
                )

        for a in [1, 2, 5, 16]:
            for bit in [Bit(0), Bit(1)]:
                rnd_str = rnd_bit_string(a)
                bv = BitVector[a](rnd_str)
                bit_left = bit @ bv
                bit_right = bv @ bit

                self.assertTrue(bit_left.width == a + 1)
                self.assertTrue(bit_right.width == a + 1)

                if bit:
                    self.assertTrue(bit_left == BitVector[a + 1]("1" + rnd_str))
                    self.assertTrue(bit_right == BitVector[a + 1](rnd_str + "1"))
                else:
                    self.assertTrue(bit_left == BitVector[a + 1]("0" + rnd_str))
                    self.assertTrue(bit_right == BitVector[a + 1](rnd_str + "0"))
