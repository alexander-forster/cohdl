import cohdl
from cohdl import std
from cohdl import Port, Bit, Signal
import unittest


def gen_classes(default_val):
    class PushWithoutDefault_1(cohdl.Entity):
        clk = Port.input(Bit)

        def architecture(self):
            s = Signal[Bit](default_val)

            @std.sequential(std.Clock(self.clk))
            def proc():
                s.push = True

    class PushWithoutDefault_2(cohdl.Entity):
        clk = Port.input(Bit)

        def architecture(self):
            s = Signal[Bit](default_val)

            @std.sequential(std.Clock(self.clk))
            def proc():
                nonlocal s
                s ^= True

    class PushWithoutDefault_3(cohdl.Entity):
        clk = Port.input(Bit)

        def architecture(self):
            class Wrapper:
                s = Signal[Bit](default_val)

            @std.sequential(std.Clock(self.clk))
            def proc():
                Wrapper.s ^= True

    return PushWithoutDefault_1, PushWithoutDefault_2, PushWithoutDefault_3


class SynthesizableTester(unittest.TestCase):
    def test_push_without_default(self):
        # check, that push fails if no default value is provided
        a, b, c = gen_classes(None)

        self.assertRaises(
            AssertionError,
            std.VhdlCompiler._to_ir,
            a,
        )

        self.assertRaises(
            AssertionError,
            std.VhdlCompiler._to_ir,
            b,
        )

        self.assertRaises(
            AssertionError,
            std.VhdlCompiler._to_ir,
            c,
        )

    def test_push_with_default(self):
        # check, that the compilation works if a default value is provided
        a, b, c = gen_classes(False)

        std.VhdlCompiler._to_ir(a)
        std.VhdlCompiler._to_ir(b)
        std.VhdlCompiler._to_ir(c)
