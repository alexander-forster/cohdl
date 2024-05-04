import cohdl
from cohdl import std
import unittest


class ReturnFromConcurrent_1(cohdl.Entity):

    def architecture(self):
        @cohdl.concurrent_context
        def logic():
            return


class ReturnFromConcurrent_2(cohdl.Entity):

    def architecture(self):
        @std.concurrent
        def logic():
            return


class ReturnFromSequential_1(cohdl.Entity):

    def architecture(self):
        @cohdl.sequential_context
        def logic():
            return


class ReturnFromSequential_2(cohdl.Entity):

    def architecture(self):
        @std.sequential
        def logic():
            return


class ReturnFromSequential_3(cohdl.Entity):

    def architecture(self):
        @std.sequential
        async def logic():
            return


class ReturnFromSequential_4(cohdl.Entity):

    def architecture(self):
        @std.sequential
        async def logic():
            await std.tick()
            return


class SynthesizableTester(unittest.TestCase):
    def test_invalid_returns(self):
        self.assertRaises(
            AssertionError, std.VhdlCompiler.to_string, ReturnFromConcurrent_1
        )

        std.VhdlCompiler.to_string(ReturnFromConcurrent_2)

        self.assertRaises(
            AssertionError, std.VhdlCompiler.to_string, ReturnFromSequential_1
        )

        std.VhdlCompiler.to_string(ReturnFromSequential_2)

        self.assertRaises(
            AssertionError, std.VhdlCompiler.to_string, ReturnFromSequential_3
        )

        self.assertRaises(
            AssertionError, std.VhdlCompiler.to_string, ReturnFromSequential_4
        )
