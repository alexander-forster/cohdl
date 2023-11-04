import cohdl
from cohdl import std
from cohdl import Port, Bit
import unittest


def make_test(max_duration: int | std.Duration, duration: int | std.Duration):
    class TestEntity(cohdl.Entity):
        clk = Port.input(Bit)

        def architecture(self):
            waiter = std.Waiter(max_duration)

            @std.sequential(std.Clock(self.clk, frequency=std.GHz(1)))
            async def logic():
                await waiter.wait_for(duration)

    return TestEntity


class SynthesizableTester(unittest.TestCase):
    def test_working(self):
        for waiter, duration in [
            (10, 10),
            (20, 20),
            (1, 1),
            (1, std.ns(1)),
            (std.ns(10), 10),
            (std.ns(11), 8),
            (std.ns(12), std.ps(12000)),
        ]:
            std.VhdlCompiler.to_string(make_test(waiter, duration))

    def test_now_working(self):
        for waiter, duration in [
            (10, 11),
            (20, 21),
            (1, 2),
            (1, 0),
            (1, std.ns(2)),
            (std.ns(10), 11),
            (std.ns(11), std.ps(12000)),
        ]:
            self.assertRaises(
                AssertionError, std.VhdlCompiler.to_string, make_test(waiter, duration)
            )
