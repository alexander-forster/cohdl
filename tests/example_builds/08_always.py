import cohdl
from cohdl import Bit, BitVector, Port, Clock, always


class Simple(cohdl.Entity):
    clk = Port.input(Bit)
    sw = Port.input(BitVector[16])
    led = Port.output(BitVector[16])

    def architecture(self):
        clock = Clock(self.clk)

        @cohdl.sequential(clock)
        def logic():
            z = always(self.sw | self.sw)
            self.led <<= z


#
# compile to vhdl
#

if __name__ == "__main__":
    compiler = cohdl.ToVhdl()
    result = compiler.apply(Simple)
    result.write_dir("tests/reference_builds/bin")
