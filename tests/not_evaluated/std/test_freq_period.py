import unittest

from cohdl import std


class FreqPeriodTester(unittest.TestCase):
    def test_frequency(self):
        for n in [1, 500, 1000, 123456]:
            for f in [std.Frequency(n), std.Frequency.hertz(n)]:
                assert f.hertz() == n
                assert f.kilohertz() == n / 1000.0
                assert f.megahertz() == n / 1000000.0
                assert f.gigahertz() == n / 1000000000.0
                assert f == std.Frequency(n)
                assert f == std.Frequency.hertz(n)
                assert f == std.Frequency.kilohertz(n / 1000)
                assert f == std.Frequency.megahertz(n / 1000000)
                assert f == std.Frequency.gigahertz(n / 1000000000)

                assert f.period() == std.Period(1 / n)

    def test_period(self):
        for n in [1, 500, 1000, 123456]:
            for p in [std.Period(n), std.Period.seconds(n)]:

                assert p.seconds() == n
                assert p.milliseconds() == n * 1000
                assert p.microseconds() == n * 1000000
                assert p.nanoseconds() == n * 1000000000
                assert p.picoseconds() == n * 1000000000000

                assert p == std.Period(n)
                assert p == std.Period.seconds(n)
                assert p == std.Period.milliseconds(1000 * n)
                assert p == std.Period.microseconds(1000000 * n)
                assert p == std.Period.nanoseconds(1000000000 * n)
                assert p == std.Period.picoseconds(1000000000000 * n)

                p_s = std.Period.seconds(n)
                p_ms = std.Period.milliseconds(1000 * n)
                p_us = std.Period.microseconds(1000000 * n)
                p_ns = std.Period.nanoseconds(1000000000 * n)
                p_ps = std.Period.picoseconds(1000000000000 * n)

                assert p_s == p_ms
                assert p_s == p_us
                assert p_s == p_ns
                assert p_s == p_ps

                assert p_ms == p_ms
                assert p_ms == p_us
                assert p_ms == p_ns
                assert p_ms == p_ps

                assert p_us == p_ms
                assert p_us == p_us
                assert p_us == p_ns
                assert p_us == p_ps

                assert p_ps == p_ms
                assert p_ps == p_us
                assert p_ps == p_ns
                assert p_ps == p_ps

                assert p.frequency() == std.Frequency(1 / n)
