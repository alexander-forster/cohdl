import cohdl
from cohdl import Bit, BitVector, Port, Clock, Reset, Signal


class Simple(cohdl.Entity):
    clk = Port.input(Bit)
    reset = Port.input(Bit)
    sw = Port.input(BitVector[16])
    led = Port.output(BitVector[16])

    def architecture(self):
        clock = Clock(self.clk)
        reset = Reset(self.reset)

        a = Signal(Bit, name="signal_a")
        b = Signal(Bit, 0, name="signal_b")

        @cohdl.sequential(clock, reset)
        async def logic():
            nonlocal a, b

            b <<= self.sw[15] | self.sw[14]

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
            self.led[10] <<= z | d


#
# compile to vhdl
#

if __name__ == "__main__":
    compiler = cohdl.ToVhdl()
    result = compiler.apply(Simple)
    result.write_dir("tests/reference_builds/bin")
