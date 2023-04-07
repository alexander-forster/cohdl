import cohdl
from cohdl import (
    Bit,
    BitVector,
    Unsigned,
    Port,
    select_with,
    Signal,
    Constant,
    Integer,
    Variable,
)


def seven_seg(inp: Signal[BitVector]):
    return select_with(
        inp,
        {
            "0000": BitVector(7, "1000000"),
            "0001": BitVector(7, "1111001"),
            "0010": BitVector(7, "0100100"),
            "0011": BitVector(7, "0110000"),
            "0100": BitVector(7, "0011001"),
            "0101": BitVector(7, "0010010"),
            "0110": BitVector(7, "0000010"),
            "0111": BitVector(7, "1111000"),
            "1000": BitVector(7, "0000000"),
            "1001": BitVector(7, "0010000"),
            "1010": BitVector(7, "0001000"),
            "1011": BitVector(7, "0000011"),
            "1100": BitVector(7, "1000110"),
            "1101": BitVector(7, "0100001"),
            "1110": BitVector(7, "0000110"),
            "1111": BitVector(7, "0001110"),
        },
    )


class SevenSegment(cohdl.Entity):
    clk = Port.input(Bit())

    sw = Port.input(BitVector(16))
    led = Port.output(BitVector(16))

    sseg_ca = Port.output(BitVector(7))
    sseg_an = Port.output(BitVector(8))

    def architecture(self):
        @cohdl.sequential(cohdl.Clock(self.clk))
        async def process(x=Variable(Bit(0))):
            self.sseg_ca.next = seven_seg(self.sw.lsb(4))


def one_hot(vector):
    width = len(vector)
    if width == 1:
        return vector

    half = width // 2

    lower = vector.lsb(half)
    upper = vector.msb(rest=half)

    return (
        False
        if (lower and upper) or (not lower and not upper)
        else (one_hot(lower) | one_hot(upper))
    )


#
# compile to vhdl
#

if __name__ == "__main__":
    compiler = cohdl.ToVhdl()
    result = compiler.apply(SevenSegment)
    result.write_dir("tests/reference_builds/bin")
