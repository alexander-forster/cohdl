import cohdl
from cohdl import Bit, BitVector, Port, Clock, Null


class _When:
    def __init__(self, cond, default):
        self.cond = cond
        self.default = default

    def __call__(self, arg):
        return arg if self.cond else self.default


def when(cond, default):
    return _When(cond, default)


class Simple(cohdl.Entity):
    clk = Port.input(Bit)
    sw = Port.input(BitVector[16])
    led = Port.output(BitVector[16])

    def architecture(self):
        clock = Clock(self.clk)

        @cohdl.sequential(clock)
        def logic():
            when_sw = when(self.sw[0], Null)

            self.led[0] <<= when_sw(Bit(1))
            self.led[1] <<= when_sw(self.led[2])


#
# compile to vhdl
#

if __name__ == "__main__":
    compiler = cohdl.ToVhdl()
    result = compiler.apply(Simple)
    result.write_dir("tests/reference_builds/bin")
