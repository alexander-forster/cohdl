import unittest

from cohdl import std
from cohdl import BitVector


class RegenerateDefaultsTester(unittest.TestCase):
    def test_regenerate_defaults(self):
        def normal(arg=[1, 2, 3]):
            return arg

        @std.regenerate_defaults
        def decorated(arg=[1, 2, 3]):
            return arg

        normal_a = normal()
        normal_b = normal()

        decorated_a = decorated()
        decorated_b = decorated()

        assert normal_a is normal_b
        assert decorated_a is not decorated_b
