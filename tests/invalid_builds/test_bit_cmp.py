import cohdl
from cohdl import std
from cohdl import Port, Bit, BitState
import unittest


def genEntity(other, reverse, ne):
    class CmpBit(cohdl.Entity):
        sig_bit = Port.input(Bit)
        sig_out = Port.output(bool)

        def architecture(self):
            @std.concurrent
            def logic():
                if ne:
                    if not reverse:
                        self.sig_bit == other
                    else:
                        other == self.sig_bit
                else:
                    if not reverse:
                        self.sig_bit != other
                    else:
                        other != self.sig_bit

    return CmpBit


class CmpBitTester(unittest.TestCase):
    def test_cmp_bit(self):
        # check that Bits can only be compared with other Bits or BitStates

        for reverse in (True, False):
            for ne in (True, False):
                for other in (
                    True,
                    False,
                    0,
                    1,
                    2,
                    3,
                    4,
                    -1,
                    -2,
                    0.0,
                    0.1,
                    1.0,
                    "0",
                    "1",
                    "2",
                    "asdfsfasdf",
                    "Z",
                    "",
                    (),
                    [],
                    ...,
                ):
                    # check that compiler rejects input
                    self.assertRaises(
                        AssertionError,
                        std.VhdlCompiler.to_string,
                        genEntity(other, reverse=reverse, ne=ne),
                    )

                for other in (
                    Bit(True),
                    Bit(False),
                    BitState.HIGH,
                    BitState.LOW,
                    BitState.DONT_CARE,
                ):
                    std.VhdlCompiler.to_string(genEntity(other, reverse=reverse, ne=ne))
