import unittest

from cohdl import op, Unsigned, Signed, Integer


class OperationTester(unittest.TestCase):
    def test_unsigned(self):

        for wa in (1, 2, 3, 4):
            for wb in (1, 2, 3, 4):
                ua = Unsigned[wa]()
                ub = Unsigned[wb]()

                assert (ua + ub).width == max(wa, wb)
                assert (ua - ub).width == max(wa, wb)
                assert (ua * ub).width == wa + wb
                assert (ua // ub).width == wa
                assert op.truncdiv(ua, ub).width == wa
                assert op.floordiv(ua, ub).width == wa
                assert (ua % ub).width == wb
                assert op.mod(ua, ub).width == wb
                assert op.rem(ua, ub).width == wb

        for w in (1, 2, 3, 4, 5):
            u = Unsigned[w]()
            for val in (-100, -1, -2, -3, 0, 1, 2, 3, 4, 5, 100):
                for wrap in (True, False):
                    if wrap:
                        i = Integer(val)
                    else:
                        i = val

                    assert (u + i).width == w
                    assert (i - u).width == w
                    assert (u - i).width == w
                    assert (i - u).width == w
                    assert (u * i).width == 2 * w
                    assert (i * u).width == 2 * w

                    assert op.truncdiv(u, i).width == w
                    assert op.truncdiv(i, u).width == w

                    assert op.mod(u, i).width == w
                    assert op.mod(i, u).width == w

                    assert op.rem(u, i).width == w
                    assert op.rem(i, u).width == w

    def test_signed(self):

        for wa in (1, 2, 3, 4):
            for wb in (1, 2, 3, 4):
                ua = Signed[wa]()
                ub = Signed[wb]()
                assert (ua - ub).width == max(wa, wb)

                assert (ua + ub).width == max(wa, wb)
                assert (ua - ub).width == max(wa, wb)
                assert (ua * ub).width == wa + wb
                assert op.truncdiv(ua, ub).width == wa
                assert (ua % ub).width == wb
                assert op.mod(ua, ub).width == wb
                assert op.rem(ua, ub).width == wb

        for w in (1, 2, 3, 4, 5):
            u = Signed[w]()

            min_val = -(2 ** (w - 1))
            max_val = 2 ** (w - 1) - 1

            assert u.min() == min_val
            assert u.max() == max_val

            for i in (-100, -1, -2, -3, 0, 1, 2, 3, 4, 5, 100):

                if min_val <= i <= max_val:
                    assert (u + i).width == w
                    assert (i + u).width == w

                    if i != min_val:
                        assert (u - i).width == w
                        assert (i - u).width == w
                    else:
                        pass
                else:
                    pass

                assert (u * i).width == 2 * w
                assert (i * u).width == 2 * w

                assert op.truncdiv(u, i).width == w
                assert op.truncdiv(i, u).width == w

                assert op.mod(u, i).width == w
                assert op.mod(i, u).width == w

                assert op.rem(u, i).width == w
                assert op.rem(i, u).width == w
