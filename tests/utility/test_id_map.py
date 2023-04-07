import unittest

from cohdl.utility import IdMap


class BitStateTester(unittest.TestCase):
    def test_basic(self):
        map = IdMap()

        self.assertTrue(len(map) == 0)

        a = []
        A = "A"

        b = {1, 2, 3}
        B = "B"

        map[a] = A
        map[b] = B

        self.assertTrue(a in map)
        self.assertTrue(b in map)
        self.assertTrue(id(a) in map)
        self.assertTrue(id(b) in map)
        self.assertTrue(len(map) == 2)

        self.assertTrue(map[a] is A)
        self.assertTrue(map[b] is B)

    def test_assertations(self):
        map = IdMap()

        def set_item(map, key, value):
            map[key] = value

        self.assertRaises(AssertionError, set_item, map, "asdf", 1)

    def test_compare(self):
        map_a = IdMap()
        map_b = IdMap()

        self.assertTrue(map_a == map_a)
        self.assertTrue(map_a == map_b)

        key_1 = []
        item_1 = 1

        map_a[key_1] = item_1

        self.assertFalse(map_a == map_b)
        self.assertTrue(map_a != map_b)

        map_b[key_1] = item_1

        self.assertFalse(map_a != map_b)
        self.assertTrue(map_a == map_b)

        key_2a = []
        key_2b = []
        item_2a = [1, 2, "asdf", 1]
        item_2b = [1, 2, "asdf", 1]

        map_a[key_2a] = item_2a

        self.assertFalse(map_a == map_b)
        self.assertTrue(map_a != map_b)

        map_b[key_2a] = item_2b

        self.assertFalse(map_a != map_b)
        self.assertTrue(map_a == map_b)

        del map_b[key_2a]

        self.assertTrue(len(map_b) == 1)

        map_b[key_2b] = item_2b

        self.assertFalse(map_a == map_b)
        self.assertTrue(map_a != map_b)

    def test_merge(self):
        map_a = IdMap()
        map_b = IdMap()

        key_a = []
        item_a = [1]

        key_b = []
        item_b = [2]

        key_c = []
        item_c1 = [3]
        item_c2 = [4]

        map_a[key_a] = item_a
        map_b[key_a] = item_a

        map_a[key_b] = item_b

        map_a[key_c] = item_c1
        map_b[key_c] = item_c2

        map_result = IdMap.merge(map_a, map_b, on_conflict=lambda a, b: a + b)

        self.assertTrue(len(map_result) == 3)
        self.assertTrue(map_result[key_a] is item_a)
        self.assertTrue(map_result[key_b] is item_b)
        self.assertTrue(map_result[key_c] == [3, 4])
