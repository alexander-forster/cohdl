import unittest

from cohdl import Unsigned, Signed, Entity, pyeval
from cohdl import std


class CaptureTester(unittest.TestCase):
    def test_concurrent(self):
        loop_values = [*range(8)]
        captured = []

        @pyeval
        def capture(val):
            captured.append(val)

        #
        #
        #

        class Entity_A(Entity):
            def architecture(self):
                for loop in loop_values:

                    @std.concurrent
                    def logic():
                        capture(loop)

        std.VhdlCompiler.to_string(Entity_A)
        assert captured == loop_values
        captured = []

        #
        #
        #

        class Entity_B(Entity):
            def architecture(self):
                for loop in loop_values:

                    @std.concurrent(capture_lazy=True)
                    def logic():
                        capture(loop)

        std.VhdlCompiler.to_string(Entity_B)
        assert captured == [loop_values[-1]] * len(loop_values)
        captured = []

        #
        #
        #

    def test_sequential(self):
        loop_values = [*range(8)]
        captured = []

        @pyeval
        def capture(val):
            captured.append(val)

        #
        #
        #

        class Entity_A(Entity):
            def architecture(self):
                for loop in loop_values:

                    @std.sequential
                    def logic():
                        capture(loop)

        std.VhdlCompiler.to_string(Entity_A)
        assert captured == loop_values
        captured = []

        #
        #
        #

        class Entity_B(Entity):
            def architecture(self):
                for loop in loop_values:

                    @std.sequential(capture_lazy=True)
                    def logic():
                        capture(loop)

        std.VhdlCompiler.to_string(Entity_B)
        assert captured == [loop_values[-1]] * len(loop_values)
        captured = []
