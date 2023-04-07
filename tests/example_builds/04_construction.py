import cohdl
from cohdl import Bit, BitVector, Port, Clock, Signal


class Simple(cohdl.Entity):
    clk = Port.input(Bit)
    sw = Port.input(BitVector[16])
    led = Port.output(BitVector[16])

    def architecture(self):
        clock = Clock(self.clk)

        a = Signal(Bit)
        b = Signal(Bit, 0)

        @cohdl.sequential(clock)
        async def logic():
            c = Signal(Bit)
            d = Signal(self.sw[0])
            d <<= self.sw[7]

            self.led[0] <<= self.sw[1]
            self.led[4:1] <<= self.sw[3:0]
            self.led[5] <<= a
            self.led[6] <<= b
            self.led[7] <<= c
            self.led[8] <<= d

            z = Signal(c | d)

            await self.sw[5]

            self.led[9] <<= d
            self.led[10] <<= z


#
# compile to vhdl
#

if __name__ == "__main__":
    compiler = cohdl.ToVhdl()
    result = compiler.apply(Simple)
    result.write_dir("tests/reference_builds/bin")
