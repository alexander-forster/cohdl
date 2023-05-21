import unittest

from cohdl import Unsigned, Signed


class ResizeTester(unittest.TestCase):
    def test_signed(self):
        for inp_width in [1, 3, 5]:
            for nr in range(-(2 ** (inp_width - 1)), 2 ** (inp_width - 1)):
                s = Signed[inp_width](nr)

                for w in [5, 6, 10, 12]:
                    for z in [None, 0, 1, 2, 4]:
                        if z is None:
                            r = s.resize(w)
                            z = 0
                        else:
                            if inp_width + z > w:
                                continue
                            r = s.resize(w, zeros=z)

                        assert r is not s
                        assert r.width == w
                        assert r == nr * 2**z

    def test_unsigned(self):
        for inp_width in [1, 3, 5]:
            for nr in range(0, 2**inp_width):
                s = Unsigned[inp_width](nr)

                for w in [5, 6, 10, 12]:
                    for z in [None, 0, 1, 2, 4]:
                        if z is None:
                            r = s.resize(w)
                            z = 0
                        else:
                            if inp_width + z > w:
                                continue
                            r = s.resize(w, zeros=z)

                        assert r is not s
                        assert r.width == w
                        assert r == nr * 2**z
