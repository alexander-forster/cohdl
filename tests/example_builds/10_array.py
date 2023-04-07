import cohdl
from cohdl import Bit, BitVector, Port, Clock, Array, Signal, Unsigned


class Simple(cohdl.Entity):
    clk = Port.input(Bit)
    sw = Port.input(BitVector[16])
    led = Port.output(BitVector[16])

    def architecture(self):
        clock = Clock(self.clk)

        mem = Signal(Array[BitVector[32], 128])
        index = Signal(Unsigned[4], 0)
        x = Bit(1)
        y = Signal(Bit)

        @cohdl.sequential(clock)
        def logic():
            mem[index + 1] <<= mem[index + 1]
            y.next = True


#
# compile to vhdl
#

if __name__ == "__main__":
    compiler = cohdl.ToVhdl()
    result = compiler.apply(Simple)
    result.write_dir("tests/reference_builds/bin")
