import cohdl
from cohdl import std
from cohdl import Port, Bit
import unittest


from cohdl import Bit, Port
from cohdl import std


class Base:
    def __init__(self, val):
        self._val = val

    def __ilshift__(self, other):
        self._val <<= other._val
        return self

    def __bool__(self):
        return bool(self._val)


class Derived(Base):
    def __bool__(self):
        return not self._val


def find_first_true(*args):
    for arg in args:
        if arg:
            return arg
    else:
        return args[0]


class DifferentInstances_ok(cohdl.Entity):
    a = Port.input(Bit)
    b = Port.input(Bit)
    c = Port.input(Bit)

    def architecture(self):
        @std.sequential
        def logic():
            base_a = Base(self.a)
            base_b = Base(self.b)
            derived_c = Derived(self.c)

            res = find_first_true(base_a, base_b, derived_c)

            isinstance(res, Base)


class DifferentInstances_err(cohdl.Entity):
    a = Port.input(Bit)
    b = Port.input(Bit)
    c = Port.input(Bit)

    def architecture(self):
        @std.sequential
        def logic():
            base_a = Base(self.a)
            base_b = Base(self.b)
            derived_c = Derived(self.c)

            res = find_first_true(base_a, base_b, derived_c)

            isinstance(res, Derived)


class DifferentSubclasses_ok(cohdl.Entity):
    a = Port.input(Bit)
    b = Port.input(Bit)
    c = Port.input(Bit)

    def architecture(self):
        @std.sequential
        def logic():
            base_a = Base(self.a)
            base_b = Base(self.b)
            derived_c = Derived(self.c)

            res = type(find_first_true(base_a, base_b, derived_c))

            issubclass(res, Base)


class DifferentSubclasses_err(cohdl.Entity):
    a = Port.input(Bit)
    b = Port.input(Bit)
    c = Port.input(Bit)

    def architecture(self):
        @std.sequential
        def logic():
            base_a = Base(self.a)
            base_b = Base(self.b)
            derived_c = Derived(self.c)

            res = type(find_first_true(base_a, base_b, derived_c))

            issubclass(res, Derived)


class SynthesizableTester(unittest.TestCase):
    def test_different_instances(self):
        std.VhdlCompiler.to_string(DifferentInstances_ok)

        self.assertRaises(
            AssertionError, std.VhdlCompiler.to_string, DifferentInstances_err
        )

        std.VhdlCompiler.to_string(DifferentSubclasses_ok)

        self.assertRaises(
            AssertionError, std.VhdlCompiler.to_string, DifferentSubclasses_err
        )
