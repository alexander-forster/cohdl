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
    Clock,
)

"""
def one_hot(vector):
    width = len(vector)
    if width == 1:
        return vector

    half = width // 2

    lower = vector.lsb(half)
    upper = vector.msb(rest=half)

    return (
        False if not vector or (lower and upper) else (one_hot(lower) | one_hot(upper))
    )
"""


def gen_mask_str(length):
    for x in range(length):
        result = ["0"] * length
        result[x] = "1"
        yield "".join(result)


def gen_mask_dict(length):
    return {mask_str: Bit(1) for mask_str in gen_mask_str(length)}


_masks = [None, *[gen_mask_dict(length) for length in range(1, 17)]]


def one_hot(vector):
    width = vector.width()

    if width <= 17:
        return select_with(vector, _masks[width], Bit(0))
    else:
        lower = vector.lsb(6)
        upper = vector.msb(rest=6)

        return Bit(0) if lower and upper else (one_hot(upper) or one_hot(lower))


class TestOneHot(cohdl.Entity):
    clk = Port.input(Bit())

    sw = Port.input(BitVector(16))
    led = Port.output(BitVector(16))

    sseg_ca = Port.output(BitVector(7))
    sseg_an = Port.output(BitVector(8))

    def architecture(self):
        asdf = BitVector.zeros(32)

        # @cohdl.sequential(Clock(self.clk))
        @cohdl.concurrent()
        def process():
            self.clk.next = bool(self.sw)

            # self.led[0].next = one_hot(self.sw)


#
# compile to vhdl
#

if __name__ == "__main__":
    compiler = cohdl.ToVhdl()
    result = compiler.apply(TestOneHot)
    result.write_dir("tests/reference_builds/bin")
